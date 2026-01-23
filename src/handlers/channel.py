import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
# نستورد خدمة Fal الجديدة
from src.services.fal_design import FalDesignService 

logger = logging.getLogger(__name__)

forwarder = ForwarderService()
fal_designer = FalDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # 1. فحص التكرار
    if await forwarder.redis.exists(f"bot_gen:{message.message_id}"): return

    # 2. استخراج النص
    text = message.text or message.caption or ""
    if not text: return

    # 3. الإرسال لـ Fal.ai
    logger.info("🎨 Sending to Fal.ai (Flux Pro)...")
    
    # إرسال إشعار للمستخدم بأننا نعمل
    await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    
    image_path = await fal_designer.generate_design(text, message.message_id)
    
    if image_path:
        try:
            with open(image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=f"✨ {settings.CHANNEL_HANDLE}"
                )
            
            # تسجيل وتوزيع
            await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
            await forwarder.broadcast_message(context.bot, sent.message_id)
            
            os.remove(image_path)
            return
            
        except Exception as e:
            logger.error(f"Broadcasting Failed: {e}")
    
    else:
        # في حال الفشل، ننشر النص كما هو
        logger.info("⏩ Design failed, broadcasting text.")
        await forwarder.broadcast_message(context.bot, message.message_id)