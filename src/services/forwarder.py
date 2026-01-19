import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
from telegram.error import RetryAfter, Forbidden, BadRequest, ChatNotFound
from sqlalchemy import select, update
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_msg_id: int):
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
        tasks = [self._safe_copy(bot, cid, settings.MASTER_SOURCE_ID, msg_id, model, id_col) for cid in batch]
        await asyncio.gather(*tasks)

    async def _safe_copy(self, bot, chat_id, from_chat, msg_id, model, id_col):
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await self._safe_copy(bot, chat_id, from_chat, msg_id, model, id_col)
        except (Forbidden, ChatNotFound):
            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(update(model).where(id_col == chat_id).values(is_active=False))
                    await session.commit()
            except: pass
        except Exception: pass