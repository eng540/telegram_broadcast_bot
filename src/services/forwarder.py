import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
from telegram.error import RetryAfter, Forbidden, BadRequest
from sqlalchemy import select, update, delete
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup, BroadcastLog
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_msg_id: int):
        """توزيع الرسالة وتسجيلها في السجل"""
        await self._broadcast(bot, source_msg_id, BotUser, BotUser.user_id, BotUser.is_active, "Users")
        await self._broadcast(bot, source_msg_id, TelegramChannel, TelegramChannel.chat_id, TelegramChannel.is_active, "Channels")
        await self._broadcast(bot, source_msg_id, TelegramGroup, TelegramGroup.chat_id, TelegramGroup.is_active, "Groups")

    async def _broadcast(self, bot, msg_id, model, id_col, active_col, label):
        async with AsyncSessionLocal() as session:
            result = await session.stream_scalars(select(id_col).where(active_col == True))
            batch = []
            async for chat_id in result:
                batch.append(chat_id)
                if len(batch) >= 20:
                    await self._send_batch(bot, batch, msg_id, model, id_col)
                    batch = []
                    await asyncio.sleep(0.1)
            if batch: await self._send_batch(bot, batch, msg_id, model, id_col)

    async def _send_batch(self, bot, batch, msg_id, model, id_col):
        tasks = [self._safe_copy(bot, chat_id, settings.MASTER_SOURCE_ID, msg_id, model, id_col) for chat_id in batch]
        results = await asyncio.gather(*tasks)
        
        # تسجيل الرسائل الناجحة في BroadcastLog لتمكين الحذف مستقبلاً
        async with AsyncSessionLocal() as session:
            logs = []
            for res in results:
                if res: # res = (target_chat_id, target_msg_id)
                    logs.append(BroadcastLog(source_msg_id=msg_id, target_chat_id=res[0], target_msg_id=res[1]))
            if logs:
                session.add_all(logs)
                await session.commit()

    async def _safe_copy(self, bot, chat_id, from_chat, msg_id, model, id_col):
        try:
            sent = await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
            return (chat_id, sent.message_id)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            return await self._safe_copy(bot, chat_id, from_chat, msg_id, model, id_col)
        except (Forbidden, ChatNotFound):
            await self._deactivate(model, id_col, chat_id, "Forbidden")
            return None
        except BadRequest as e:
            if "chat not found" in str(e).lower():
                await self._deactivate(model, id_col, chat_id, "Chat Not Found")
            return None
        except Exception:
            return None

    async def _deactivate(self, model, id_col, chat_id, reason):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(update(model).where(id_col == chat_id).values(is_active=False))
                await session.commit()
        except: pass

    async def delete_broadcast(self, bot: Bot, source_msg_id: int):
        """حذف الرسالة من جميع الوجهات"""
        logger.info(f"🗑️ Deleting broadcast for source: {source_msg_id}")
        async with AsyncSessionLocal() as session:
            stmt = select(BroadcastLog).where(BroadcastLog.source_msg_id == source_msg_id)
            logs = await session.scalars(stmt)
            tasks = [self._safe_delete(bot, log.target_chat_id, log.target_msg_id) for log in logs]
            await asyncio.gather(*tasks)
            # تنظيف السجل
            await session.execute(delete(BroadcastLog).where(BroadcastLog.source_msg_id == source_msg_id))
            await session.commit()

    async def _safe_delete(self, bot, chat_id, msg_id):
        try: await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except: pass