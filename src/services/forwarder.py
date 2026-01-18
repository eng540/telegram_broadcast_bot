import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
from telegram.error import RetryAfter, Forbidden, BadRequest
from sqlalchemy import select, delete
from src.database import AsyncSessionLocal
from src.models import Subscriber
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_id: int, message_id: int):
        # التحقق من Redis لمنع التكرار (Idempotency)
        key = f"broadcast_v2:{source_id}:{message_id}"
        if await self.redis.exists(key):
            logger.info(f"🔁 Message {message_id} already processed. Skipping.")
            return
        
        # تخزين المفتاح لمدة 24 ساعة
        await self.redis.set(key, 1, ex=86400)
        logger.info(f"🚀 Starting broadcast for message {message_id}...")

        async with AsyncSessionLocal() as session:
            # استخدام stream_scalars لتقليل استهلاك الذاكرة (Memory Efficient)
            stmt = select(Subscriber.chat_id)
            result = await session.stream_scalars(stmt)
            
            batch = []
            batch_size = 25  # حجم الدفعة
            count = 0

            async for chat_id in result:
                batch.append(chat_id)
                if len(batch) >= batch_size:
                    await self._process_batch(bot, batch, source_id, message_id)
                    count += len(batch)
                    batch = []
                    await asyncio.sleep(0.05) # استراحة قصيرة جداً لتجنب خنق المعالج
            
            # معالجة البقية
            if batch:
                await self._process_batch(bot, batch, source_id, message_id)
                count += len(batch)

        logger.info(f"✅ Broadcast finished. Processed {count} subscribers.")

    async def _process_batch(self, bot: Bot, batch: list, source_id: int, message_id: int):
        # تنفيذ الدفعة بشكل متوازي
        tasks = [self._safe_forward(bot, chat_id, source_id, message_id) for chat_id in batch]
        await asyncio.gather(*tasks)

    async def _safe_forward(self, bot: Bot, chat_id: int, from_chat: int, msg_id: int):
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
        except RetryAfter as e:
            # احترام قيود تيليجرام (Rate Limits)
            logger.warning(f"⏳ FloodWait: Sleeping {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self._safe_forward(bot, chat_id, from_chat, msg_id)
        except (Forbidden, BadRequest):
            # المستخدم حظر البوت أو الحساب محذوف -> تنظيف قاعدة البيانات
            async with AsyncSessionLocal() as session:
                await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
                await session.commit()
        except Exception as e:
            logger.error(f"⚠️ Error forwarding to {chat_id}: {e}")