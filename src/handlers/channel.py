import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator
from src.services.ai_background import AIBackgroundService

logger = logging.getLogger(__name__)

forwarder = ForwarderService()
image_gen = ImageGenerator()
ai_bg = AIBackgroundService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # قفل لمنع التكرار
    lock_key = f"processing_lock:{message.message_id}"
    if await forwarder.redis.get(lock_key): return
    await forwarder.redis.set(lock_key, "1", ex=60)

    text = message.text or message.caption or ""
    if not text or settings.CHANNEL_HANDLE in text: return

    logger.info("🎨 Starting AI Design Process...")
    
    # 1. الذكاء الاصطناعي يرسم الخلفية
    bg_path = await ai_bg.generate(text)
    
    if not bg_path:
        logger.warning("⚠️ AI failed to generate background. Using fallback.")
        # هنا سيعمل الكود القديم (صورة عشوائية) كاحتياط فقط
    
    # 2. دمج النص العربي (بوضوح تام) فوق خلفية الذكاء الاصطناعي
    try:
        # نمرر مسار الصورة التي رسمها AI
        image_path = await image_gen.render(text, message.message_id, bg_path)
        
        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=f"✨ {settings.CHANNEL_HANDLE}"
            )
        
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        # تنظيف الملفات
        os.remove(image_path)
        if bg_path and os.path.exists(bg_path):
            os.remove(bg_path)
            
    except Exception as e:
        logger.error(f"Design Process Failed: {e}")
        await forwarder.broadcast_message(context.bot, message.message_id)