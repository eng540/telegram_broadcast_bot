import logging
import asyncio
import redis.asyncio as redis
from telegram import Bot
from telegram.error import RetryAfter, Forbidden, BadRequest, ChatNotFound
from sqlalchemy import select, delete
from src.database import AsyncSessionLocal
# استيراد النماذج الثلاثة الجديدة
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings

logger = logging.getLogger(__name__)

class ForwarderService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)

    async def broadcast_message(self, bot: Bot, source_msg_id: int):
        """
        توزيع الرسالة على جميع الكيانات (أفراد، قنوات، مجموعات)
        بشكل منفصل وآمن.
        """
        logger.info(f"📣 Starting Broadcast for Message ID: {source_msg_id}")

        # 1. توزيع للأفراد (لاحظ استخدام BotUser.user_id)
        await self._broadcast_to_model(bot, source_msg_id, BotUser, BotUser.user_id, "Users")
        
        # 2. توزيع للقنوات (لاحظ استخدام TelegramChannel.chat_id)
        await self._broadcast_to_model(bot, source_msg_id, TelegramChannel, TelegramChannel.chat_id, "Channels")
        
        # 3. توزيع للمجموعات (لاحظ استخدام TelegramGroup.chat_id)
        await self._broadcast_to_model(bot, source_msg_id, TelegramGroup, TelegramGroup.chat_id, "Groups")

    async def _broadcast_to_model(self, bot: Bot, msg_id: int, model_class, id_column, type_name):
        """
        دالة عامة تعالج أي جدول يتم تمريره لها
        """
        async with AsyncSessionLocal() as session:
            # جلب المعرفات فقط لتقليل استهلاك الذاكرة
            result = await session.stream_scalars(select(id_column))
            
            batch = []
            count = 0
            async for chat_id in result:
                batch.append(chat_id)
                if len(batch) >= 20: # دفعة صغيرة آمنة
                    await self._process_batch(bot, batch, msg_id, model_class, id_column)
                    count += len(batch)
                    batch = []
                    await asyncio.sleep(0.1) # استراحة لتجنب حظر التكرار
            
            # معالجة البقية
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
            # احترام قوانين تيليجرام
            logger.warning(f"⏳ FloodWait: Sleeping {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self._safe_copy(bot, chat_id, from_chat, msg_id, model_class, id_column)
        
        except (Forbidden, ChatNotFound):
            # 🛑 الحذف المشروع: فقط إذا كان البوت محظوراً أو الحساب محذوفاً
            # نستخدم model_class و id_column لحذف السجل الصحيح من الجدول الصحيح
            logger.info(f"🗑️ Removing dead entity {chat_id} from {model_class.__tablename__}")
            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(delete(model_class).where(id_column == chat_id))
                    await session.commit()
            except Exception as e:
                logger.error(f"DB Cleanup Error: {e}")

        except BadRequest as e:
            # ⚠️ الحماية من الحذف الخاطئ:
            # إذا كان الخطأ تقنياً (مثل: Message not modified, Content too long)
            # لا نحذف المستخدم! نحتفظ به.
            logger.error(f"⚠️ Skipping {chat_id} (Technical Error): {e}")
        
        except Exception as e:
            logger.error(f"⚠️ Unknown Error for {chat_id}: {e}")