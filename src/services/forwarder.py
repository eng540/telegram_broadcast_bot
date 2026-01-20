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
        """توزيع وتسجيل الرسائل مع الحفاظ على التوافق"""
        await self._broadcast(
            bot,
            source_msg_id,
            BotUser,
            BotUser.user_id,
            BotUser.is_active,
            "Users",
        )
        await self._broadcast(
            bot,
            source_msg_id,
            TelegramChannel,
            TelegramChannel.chat_id,
            TelegramChannel.is_active,
            "Channels",
        )
        await self._broadcast(
            bot,
            source_msg_id,
            TelegramGroup,
            TelegramGroup.chat_id,
            TelegramGroup.is_active,
            "Groups",
        )

    async def _broadcast(self, bot, msg_id, model, id_col, active_col, label):
        async with AsyncSessionLocal() as session:
            result = await session.stream_scalars(
                select(id_col).where(active_col == True)
            )

            batch = []
            async for chat_id in result:
                batch.append(chat_id)

                if len(batch) >= 20:
                    await self._send_batch(
                        bot, batch, msg_id, model, id_col, label
                    )
                    batch = []
                    await asyncio.sleep(0.1)

            if batch:
                await self._send_batch(
                    bot, batch, msg_id, model, id_col, label
                )

    async def _send_batch(self, bot, batch, msg_id, model, id_col, label):
        """إرسال دفعة مع تسجيل النتائج"""
        tasks = [
            self._safe_copy(
                bot,
                chat_id,
                settings.MASTER_SOURCE_ID,
                msg_id,
                model,
                id_col,
                label,
            )
            for chat_id in batch
        ]
        
        results = await asyncio.gather(*tasks)
        
        # تسجيل الرسائل الناجحة فقط
        async with AsyncSessionLocal() as session:
            logs_to_add = []
            for result in results:
                if result:  # result يحتوي على (target_chat_id, target_msg_id)
                    target_chat_id, target_msg_id = result
                    logs_to_add.append(BroadcastLog(
                        source_msg_id=msg_id,
                        target_chat_id=target_chat_id,
                        target_msg_id=target_msg_id
                    ))
            
            if logs_to_add:
                session.add_all(logs_to_add)
                await session.commit()

    async def _safe_copy(
        self, bot, chat_id, from_chat, msg_id, model, id_col, label
    ):
        """نسخ آمن للرسالة مع تسجيل الأخطاء"""
        try:
            sent = await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=from_chat,
                message_id=msg_id,
            )
            
            # إرجاع البيانات للتسجيل
            return (chat_id, sent.message_id)

        except RetryAfter as e:
            logger.warning(
                f"⏳ RetryAfter {e.retry_after}s → {label} {chat_id}"
            )
            await asyncio.sleep(e.retry_after)
            return await self._safe_copy(
                bot, chat_id, from_chat, msg_id, model, id_col, label
            )

        except Forbidden:
            logger.warning(
                f"🚫 Forbidden → deactivating {label} {chat_id}"
            )
            await self._deactivate(chat_id, model, id_col)
            return None

        except BadRequest as e:
            msg = str(e).lower()

            if "chat not found" in msg:
                logger.warning(
                    f"❌ Chat not found → deactivating {label} {chat_id}"
                )
                await self._deactivate(chat_id, model, id_col)
            else:
                logger.error(
                    f"⚠️ BadRequest for {label} {chat_id}: {e}"
                )
            
            return None

        except Exception as e:
            logger.exception(
                f"💥 Unexpected error for {label} {chat_id}: {e}"
            )
            return None

    async def _deactivate(self, chat_id, model, id_col):
        """تعطيل المحادثة"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(model)
                    .where(id_col == chat_id)
                    .values(is_active=False)
                )
                await session.commit()
        except Exception as e:
            logger.error(
                f"Failed to deactivate chat {chat_id}: {e}"
            )

    # --- وظيفة الحذف الجماعي ---
    async def delete_broadcast(self, bot: Bot, source_msg_id: int):
        """حذف الرسالة من عند الجميع"""
        logger.info(f"🗑️ Deleting broadcast for source msg: {source_msg_id}")
        
        async with AsyncSessionLocal() as session:
            # جلب كل النسخ المرسلة
            stmt = select(BroadcastLog).where(BroadcastLog.source_msg_id == source_msg_id)
            result = await session.scalars(stmt)
            
            tasks = []
            for log in result:
                tasks.append(self._safe_delete(bot, log.target_chat_id, log.target_msg_id))
            
            # حذف جميع الرسائل
            await asyncio.gather(*tasks)
            
            # تنظيف السجل
            await session.execute(
                delete(BroadcastLog).where(BroadcastLog.source_msg_id == source_msg_id)
            )
            await session.commit()
            
        logger.info(f"✅ Deleted {len(tasks)} messages and cleaned logs")

    async def _safe_delete(self, bot, chat_id, msg_id):
        """حذف آمن للرسالة"""
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            return True
        except Forbidden:
            logger.warning(f"🚫 Cannot delete message {msg_id} from {chat_id} (Forbidden)")
        except BadRequest as e:
            if "message to delete not found" not in str(e).lower():
                logger.warning(f"⚠️ Failed to delete message {msg_id} from {chat_id}: {e}")
        except Exception as e:
            logger.error(f"💥 Error deleting message {msg_id} from {chat_id}: {e}")
        
        return False