import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator # الخطة البديلة (HTML)
from src.services.fal_design import FalDesignService # الخطة الأساسية (AI)

logger = logging.getLogger(__name__)

forwarder = ForwarderService()
html_renderer = ImageGenerator()
fal_designer = FalDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # الحماية من التكرار
    redis_key = f"bot_processed:{message.message_id}"
    if await forwarder.redis.exists(redis_key): return

    text = message.text or message.caption or ""
    if not text: return

    logger.info(f"📩 Processing Post...")
    
    final_image_path = None
    used_engine = "NONE"

    # --- المحاولة 1: الذكاء الاصطناعي (Fal.ai / Gemini 3) ---
    # نستخدمه للنصوص القصيرة والمتوسطة (أقل من 200 حرف) لضمان دقة الكتابة
    if len(text) < 200:
        try:
            await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
            final_image_path = await fal_designer.generate_design(text, message.message_id)
            if final_image_path: used_engine = "Fal_AI"
        except Exception as e:
            logger.warning(f"⚠️ Fal.ai skipped: {e}")

    # --- المحاولة 2: الخطة البديلة (HTML Engine) ---
    # إذا فشل AI أو كان النص طويلاً جداً
    if not final_image_path:
        logger.info("🎨 Switching to HTML Engine (Fallback)...")
        try:
            # هنا نستخدم HTML لرسم النص، ونختار خلفية عشوائية جميلة
            final_image_path = await html_renderer.render(text, message.message_id)
            used_engine = "HTML_Engine"
        except Exception as e:
            logger.error(f"❌ All engines failed: {e}")

    # --- النشر ---
    try:
        await forwarder.redis.set(redis_key, "1", ex=86400)

        if final_image_path:
            with open(final_image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=f"✨ {settings.CHANNEL_HANDLE}"
                )
            
            logger.info(f"✅ Published using {used_engine}")
            await forwarder.broadcast_message(context.bot, sent.message_id)
            os.remove(final_image_path)
        else:
            # إذا فشل كل شيء، انشر النص
            await forwarder.broadcast_message(context.bot, message.message_id)

    except Exception as e:
        logger.error(f"Broadcast Error: {e}")