import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
# تصحيح الاستدعاء: حذفنا ChatNotFound لأنها غير موجودة
from telegram.error import RetryAfter, Forbidden, BadRequest
from sqlalchemy import select, delete
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_msg_id: int):
        logger.info(f"📣 Starting Broadcast for Message ID: {source_msg_id}")

        await self._broadcast_to_model(bot, source_msg_id, BotUser, BotUser.user_id, "Users")
        await self._broadcast_to_model(bot, source_msg_id, TelegramChannel, TelegramChannel.chat_id, "Channels")
        await self._broadcast_to_model(bot, source_msg_id, TelegramGroup, TelegramGroup.chat_id, "Groups")

    async def _broadcast_to_model(self, bot: Bot, msg_id: int, model_class, id_column, type_name):
        async with AsyncSessionLocal() as session:
            result = await session.stream_scalars(select(id_column))
            
            batch = []
            count = 0
            async for chat_id in result:
                batch.append(chat_id)
                if len(batch) >= 20:
                    await self._process_batch(bot, batch, msg_id, model_class, id_column)
                    count += len(batch)
                    batch = []
                    await asyncio.sleep(0.1)
            
            if batch:
                await self._process_batch(bot, batch, msg_id, model_class, id_column)
                count += len(batch)
            
            logger.info(f"✅ Finished {type_name}: Processed {count}")

    async def _process_batch(self, bot: Bot, batch: list, msg_id: int, model_class, id_column):
        tasks = [self._safe_copy(bot, chat_id, settings.MASTER_SOURCE_ID, msg_id, model_class, id_column) for chat_id in batch]
        await asyncio.gather(*tasks)

    async def _safe_copy(self, bot: Bot, chat_id: int, from_chat: int, msg_id: int, model_class, id_column):
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
        
        except RetryAfter as e:
            logger.warning(f"⏳ FloodWait: Sleeping {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self._safe_copy(bot, chat_id, from_chat, msg_id, model_class, id_column)
        
        except Forbidden:
            # 🛑 المستخدم حظر البوت (هذا الخطأ صحيح وموجود)
            logger.info(f"🗑️ Forbidden: Removing {chat_id}")
            await self._delete_entry(model_class, id_column, chat_id)

        except BadRequest as e:
            # 🛑 هنا نلتقط خطأ "Chat not found" الذي يأتي تحت مظلة BadRequest
            error_msg = str(e)
            if "Chat not found" in error_msg or "chat not found" in error_msg:
                logger.info(f"🗑️ Chat Not Found: Removing {chat_id}")
                await self._delete_entry(model_class, id_column, chat_id)
            else:
                # أخطاء تقنية أخرى (لا نحذف المستخدم)
                logger.error(f"⚠️ Technical Skip {chat_id}: {e}")
        
        except Exception as e:
            logger.error(f"⚠️ Unknown Error for {chat_id}: {e}")

    async def _delete_entry(self, model_class, id_column, chat_id):
        """دالة مساعدة للحذف من قاعدة البيانات"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(delete(model_class).where(id_column == chat_id))
                await session.commit()
        except Exception as e:
            logger.error(f"DB Cleanup Error: {e}")