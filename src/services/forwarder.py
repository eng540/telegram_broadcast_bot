import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
from telegram.error import RetryAfter, Forbidden, BadRequest
from sqlalchemy import select, delete
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup # النماذج الثلاثة
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_msg_id: int):
        """توزيع الرسالة على: الأفراد، القنوات، المجموعات"""
        
        # 1. الأفراد
        await self._broadcast_to_model(bot, source_msg_id, BotUser, BotUser.user_id)
        
        # 2. القنوات
        await self._broadcast_to_model(bot, source_msg_id, TelegramChannel, TelegramChannel.chat_id)
        
        # 3. المجموعات
        await self._broadcast_to_model(bot, source_msg_id, TelegramGroup, TelegramGroup.chat_id)

    async def _broadcast_to_model(self, bot: Bot, msg_id: int, model_class, id_column):
        async with AsyncSessionLocal() as session:
            result = await session.stream_scalars(select(id_column))
            
            batch = []
            async for chat_id in result:
                batch.append(chat_id)
                if len(batch) >= 25:
                    await self._process_batch(bot, batch, msg_id, model_class, id_column)
                    batch = []
                    await asyncio.sleep(0.05)
            
            if batch:
                await self._process_batch(bot, batch, msg_id, model_class, id_column)

    async def _process_batch(self, bot: Bot, batch: list, msg_id: int, model_class, id_column):
        tasks = [self._safe_copy(bot, chat_id, settings.MASTER_SOURCE_ID, msg_id, model_class, id_column) for chat_id in batch]
        await asyncio.gather(*tasks)

    async def _safe_copy(self, bot: Bot, chat_id: int, from_chat: int, msg_id: int, model_class, id_column):
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await self._safe_copy(bot, chat_id, from_chat, msg_id, model_class, id_column)
        except (Forbidden, BadRequest):
            # تنظيف قاعدة البيانات إذا تم طرد البوت
            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(delete(model_class).where(id_column == chat_id))
                    await session.commit()
            except: pass
        except Exception:
            pass