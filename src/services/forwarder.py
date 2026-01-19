import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
from telegram.error import RetryAfter, Forbidden, BadRequest, ChatNotFound
from sqlalchemy import select, update  # استبدلنا delete بـ update
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_msg_id: int):
        logger.info(f"📣 Starting Smart Broadcast for Msg: {source_msg_id}")

        # نرسل فقط للنشطين (is_active=True)
        await self._broadcast_to_model(bot, source_msg_id, BotUser, BotUser.user_id, BotUser.is_active, "Users")
        await self._broadcast_to_model(bot, source_msg_id, TelegramChannel, TelegramChannel.chat_id, TelegramChannel.is_active, "Channels")
        await self._broadcast_to_model(bot, source_msg_id, TelegramGroup, TelegramGroup.chat_id, TelegramGroup.is_active, "Groups")

    async def _broadcast_to_model(self, bot: Bot, msg_id: int, model_class, id_column, active_column, type_name):
        async with AsyncSessionLocal() as session:
            # 💡 الفلتر الذهبي: اختر فقط النشطين
            stmt = select(id_column).where(active_column == True)
            result = await session.stream_scalars(stmt)
            
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
            
            logger.info(f"✅ Finished {type_name}: {count} Active Targets")

    async def _process_batch(self, bot: Bot, batch: list, msg_id: int, model_class, id_column):
        tasks = [self._safe_copy(bot, chat_id, settings.MASTER_SOURCE_ID, msg_id, model_class, id_column) for chat_id in batch]
        await asyncio.gather(*tasks)

    async def _safe_copy(self, bot: Bot, chat_id: int, from_chat: int, msg_id: int, model_class, id_column):
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
        
        except RetryAfter as e:
            logger.warning(f"⏳ FloodWait {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self._safe_copy(bot, chat_id, from_chat, msg_id, model_class, id_column)
        
        except (Forbidden, ChatNotFound):
            # 🛑 التغيير الجذري هنا: Soft Delete
            # لا نحذف السجل، بل نضع علامة "غير نشط"
            logger.info(f"💤 Deactivating entity {chat_id} (Soft Delete)")
            try:
                async with AsyncSessionLocal() as session:
                    stmt = update(model_class).where(id_column == chat_id).values(is_active=False)
                    await session.execute(stmt)
                    await session.commit()
            except Exception as e:
                logger.error(f"DB Update Error: {e}")

        except BadRequest as e:
            logger.error(f"⚠️ Technical Error for {chat_id}: {e}")
        except Exception as e:
            logger.error(f"⚠️ Unknown Error: {e}")