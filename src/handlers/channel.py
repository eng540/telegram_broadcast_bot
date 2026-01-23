# --- START OF FILE src/handlers/channel.py ---

import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator 
from src.services.fal_design import FalDesignService # ✅ المحرك الجديد

logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()
html_renderer = ImageGenerator()
fal_designer = FalDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    استراتيجية الحارس (Fal.ai Edition):
    1. Fal.ai (الجودة القصوى والسرعة)
    2. HTML Engine (الخطة البديلة)
    """
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    redis_key = f"bot_processed:{message.message_id}"
    if await forwarder.redis.exists(redis_key): return

    text = message.text or message.caption or ""
    if not text: return

    logger.info(f"📩 Post detected. Processing...")

    final_image_path = None
    used_engine = "NONE"

    # --- 1. محاولة Fal.ai ---
    try:
        await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        # لا قيود على الطول، Fal قوي جداً
        final_image_path = await fal_designer.generate_design(text, message.message_id)
        if final_image_path: used_engine = "Fal.ai"
    except Exception as e:
        logger.warning(f"⚠️ Fal.ai Skipped: {e}")

    # --- 2. الخطة البديلة (HTML) ---
    if not final_image_path:
        logger.info("🎨 Switching to HTML Engine...")
        try:
            final_image_path = await html_renderer.render(text, message.message_id)
            used_engine = "HTML_Engine"
        except Exception as e:
            logger.error(f"❌ All engines failed: {e}")

    # --- 3. النشر ---
    try:
        await forwarder.redis.set(redis_key, "1", ex=86400)

        if final_image_path:
            with open(final_image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=f"✨ {settings.CHANNEL_HANDLE}"
                )
            logger.info(f"✅ Published using {used_engine}. Broadcasting...")
            await forwarder.broadcast_message(context.bot, sent.message_id)
            os.remove(final_image_path)
        else:
            await forwarder.broadcast_message(context.bot, message.message_id)

    except Exception as e:
        logger.error(f"❌ Broadcast Error: {e}")