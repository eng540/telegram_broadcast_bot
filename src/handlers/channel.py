# --- START OF FILE src/handlers/channel.py ---

import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.google_design import GoogleDesignService
from src.services.image_gen import ImageGenerator # المحرك الكلاسيكي

logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()
google_designer = GoogleDesignService()
html_renderer = ImageGenerator()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    استراتيجية الحارس: 
    1. Nano Banana Pro (AI)
    2. Fallback to HTML Engine
    3. Broadcast
    """
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # 1. فحص التكرار عبر Redis
    # نستخدم مفتاحاً فريداً لتجنب تكرار المعالجة
    redis_key = f"bot_processed:{message.message_id}"
    if await forwarder.redis.exists(redis_key): return

    # 2. استخراج النص
    text = message.text or message.caption or ""
    if not text: return

    # 3. محاولة التصميم (Hybrid Engine)
    final_image_path = None
    used_engine = "NONE"

    # A. المحاولة الأولى: Nano Banana Pro
    # نستخدمه للنصوص التي ليست طويلة جداً لضمان جودة الكتابة
    if len(text) < 300:
        logger.info("🍌 Attempting Gemini Design...")
        try:
            # إشعار "جاري الرفع" لإيهام المستخدم بالعمل
            await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
            final_image_path = await google_designer.generate_design(text, message.message_id)
            if final_image_path: used_engine = "NanoBanana"
        except Exception as e:
            logger.error(f"⚠️ Gemini skipped: {e}")

    # B. المحاولة الثانية: HTML Renderer (The Safety Net)
    if not final_image_path:
        logger.info("🎨 Falling back to HTML Renderer...")
        try:
            final_image_path = await html_renderer.render(text, message.message_id)
            used_engine = "HTML_Engine"
        except Exception as e:
            logger.error(f"❌ HTML Engine failed: {e}")

    # 4. النشر والتوزيع
    try:
        # تسجيل المعالجة في Redis لمنع التكرار (لمدة 24 ساعة)
        await forwarder.redis.set(redis_key, "1", ex=86400)

        if final_image_path:
            # إرسال الصورة المصممة
            with open(final_image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=f"✨ {settings.CHANNEL_HANDLE}"
                )
            logger.info(f"✅ Published using {used_engine}. Broadcasting...")
            
            # توزيع الرسالة الجديدة (الصورة)
            await forwarder.broadcast_message(context.bot, sent.message_id)
            
            # تنظيف
            os.remove(final_image_path)
            
            # (اختياري) حذف الرسالة النصية الأصلية إذا أردت استبدالها تماماً
            # await message.delete() 
            
        else:
            # الملاذ الأخير: نشر النص كما هو
            logger.warning("⏩ All designs failed. Broadcasting raw text.")
            await forwarder.broadcast_message(context.bot, message.message_id)

    except Exception as e:
        logger.error(f"❌ Critical Broadcast Error: {e}")