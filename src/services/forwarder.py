import logging
import asyncio
import os
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

    # --- دالة بث الصور (الميزة الجديدة) ---
    async def broadcast_image(self, bot: Bot, image_path: str, caption: str, source_msg_id: int):
        key = f"broadcast_img:{settings.MASTER_SOURCE_ID}:{source_msg_id}"
        if await self.redis.exists(key): return
        await self.redis.set(key, 1, ex=86400)

        logger.info("🎨 Starting Image Broadcast...")

        # 1. رفع الصورة مرة واحدة للحصول على file_id لتسريع النشر
        photo_file_id = None
        try:
            # نرسل الصورة للمشرف أو أول مشترك للحصول على المعرف
            # سنستخدم معرف القناة المصدر إذا كان البوت مشرفاً فيها ويرسل لنفسه، أو أول مشترك
            async with AsyncSessionLocal() as session:
                first_sub = await session.scalar(select(Subscriber.chat_id).limit(1))
                if first_sub:
                    with open(image_path, 'rb') as f:
                        msg = await bot.send_photo(chat_id=first_sub, photo=f, caption=caption)
                        photo_file_id = msg.photo[-1].file_id
        except Exception as e:
            logger.error(f"Failed to upload initial photo: {e}")
            # في حال الفشل، سنرفع الملف لكل مستخدم (أبطأ لكن مضمون)
            photo_file_id = None

        # 2. بدء البث
        async with AsyncSessionLocal() as session:
            stmt = select(Subscriber.chat_id)
            result = await session.stream_scalars(stmt)
            
            batch = []
            async for chat_id in result:
                # تخطي الشخص الذي أرسلنا له الصورة التجريبية
                if photo_file_id and chat_id == first_sub: continue
                
                batch.append(chat_id)
                if len(batch) >= 20:
                    await self._send_photo_batch(bot, batch, image_path, photo_file_id, caption)
                    batch = []
                    await asyncio.sleep(0.05)
            
            if batch:
                await self._send_photo_batch(bot, batch, image_path, photo_file_id, caption)
        
        # تنظيف: حذف الصورة من السيرفر بعد الانتهاء
        try: os.remove(image_path)
        except: pass

    async def _send_photo_batch(self, bot: Bot, batch: list, img_path: str, file_id: str, cap: str):
        tasks = []
        for chat_id in batch:
            if file_id:
                # سريع: إرسال بالمعرف
                tasks.append(self._safe_send_photo(bot, chat_id, file_id, cap, is_file=False))
            else:
                # بطيء: رفع الملف (فقط في حال فشل الحصول على المعرف)
                tasks.append(self._safe_send_photo(bot, chat_id, img_path, cap, is_file=True))
        await asyncio.gather(*tasks)

    async def _safe_send_photo(self, bot: Bot, chat_id: int, photo, caption: str, is_file: bool):
        try:
            if is_file:
                with open(photo, 'rb') as f:
                    await bot.send_photo(chat_id=chat_id, photo=f, caption=caption)
            else:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await self._safe_send_photo(bot, chat_id, photo, caption, is_file)
        except (Forbidden, BadRequest):
            async with AsyncSessionLocal() as session:
                await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
                await session.commit()
        except Exception:
            pass

    # --- دالة البث العادي (للفيديوهات والنصوص الطويلة) ---
    async def broadcast_message(self, bot: Bot, source_id: int, message_id: int):
        # (نفس الكود القديم دون تغيير، انسخه هنا ليبقى الملف مكتملاً)
        key = f"broadcast_v2:{source_id}:{message_id}"
        if await self.redis.exists(key): return
        await self.redis.set(key, 1, ex=86400)

        async with AsyncSessionLocal() as session:
            stmt = select(Subscriber.chat_id)
            result = await session.stream_scalars(stmt)
            batch = []
            async for chat_id in result:
                batch.append(chat_id)
                if len(batch) >= 20:
                    await self._process_batch(bot, batch, source_id, message_id)
                    batch = []
                    await asyncio.sleep(0.05)
            if batch:
                await self._process_batch(bot, batch, source_id, message_id)

    async def _process_batch(self, bot: Bot, batch: list, source_id: int, message_id: int):
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
        except Exception:
            pass