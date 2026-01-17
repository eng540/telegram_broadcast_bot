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
        key = f"broadcast_v1:{source_id}:{message_id}"
        if await self.redis.exists(key):
            return
        await self.redis.set(key, 1, ex=86400)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Subscriber.chat_id))
            subscribers = result.scalars().all()

        batch_size = 20
        for i in range(0, len(subscribers), batch_size):
            batch = subscribers[i:i + batch_size]
            tasks = [self._safe_forward(bot, chat_id, source_id, message_id) for chat_id in batch]
            await asyncio.gather(*tasks)

    async def _safe_forward(self, bot: Bot, chat_id: int, from_chat: int, msg_id: int):
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await self._safe_forward(bot, chat_id, from_chat, msg_id)
        except (Forbidden, BadRequest):
            async with AsyncSessionLocal() as session:
                await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
                await session.commit()
        except Exception as e:
            logger.error(e)
