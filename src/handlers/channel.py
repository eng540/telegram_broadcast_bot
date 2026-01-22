# --- START OF FILE src/handlers/channel.py ---

import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator 
from src.services.huggingface_design import HuggingFaceDesignService 

logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()
html_renderer = ImageGenerator()
hf_designer = HuggingFaceDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    استراتيجية الحارس المحدثة:
    1. محاولة الذكاء الاصطناعي (FLUX) لكل النصوص.
    2. الفشل -> تفعيل المحرك الهندسي (HTML).
    3. النشر الآمن.
    """
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # 1. فحص التكرار (Redis)
    redis_key = f"bot_processed:{message.message_id}"
    if await forwarder.redis.exists(redis_key): return

    text = message.text or message.caption or ""
    if not text: return

    logger.info(f"📩 Post detected. Length: {len(text)}. Processing...")

    final_image_path = None
    used_engine = "NONE"

    # --- 1. محاولة Hugging Face (FLUX) ---
    # لقد أزلت شرط الطول (150 حرف) لنعطي الذكاء الاصطناعي فرصة كاملة
    try:
        # إرسال حالة "جاري الرفع" لإشعار المستخدم
        await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        
        # المحاولة
        final_image_path = await hf_designer.generate_design(text, message.message_id)
        
        if final_image_path: 
            used_engine = "HuggingFace (FLUX)"
    except Exception as e:
        logger.warning(f"⚠️ AI Skipped: {e}")

    # --- 2. الخطة البديلة (HTML Engine) ---
    # يعمل فقط إذا فشل الذكاء الاصطناعي أو عاد بـ None
    if not final_image_path:
        logger.info("🎨 Switching to HTML Engine (Fallback)...")
        try:
            final_image_path = await html_renderer.render(text, message.message_id)
            used_engine = "HTML_Engine"
        except Exception as e:
            logger.error(f"❌ All engines failed: {e}")

    # --- 3. النشر والتوزيع ---
    try:
        # تسجيل المعالجة لمنع التكرار
        await forwarder.redis.set(redis_key, "1", ex=86400)

        if final_image_path:
            with open(final_image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=f"✨ {settings.CHANNEL_HANDLE}"
                )
            logger.info(f"✅ Published using {used_engine}. Broadcasting...")
            
            # التوزيع للقنوات الأخرى
            await forwarder.broadcast_message(context.bot, sent.message_id)
            
            # تنظيف الملف
            os.remove(final_image_path)
        else:
            # في أسوأ الظروف: نشر النص فقط
            logger.warning("⏩ Design failed completely. Broadcasting raw text.")
            await forwarder.broadcast_message(context.bot, message.message_id)

    except Exception as e:
        logger.error(f"❌ Broadcast Error: {e}")