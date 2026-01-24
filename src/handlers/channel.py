#--- START OF FILE telegram_broadcast_bot-main/src/handlers/channel.py ---

import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator
from src.services.fal_design import FalDesignService 

logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()
image_gen = ImageGenerator()
fal_designer = FalDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    
    # 1. معالجة أمر الحذف (الأولوية القصوى)
    if message and message.reply_to_message and message.text and message.text.strip() == "/del":
        logger.info("🗑️ Delete command received.")
        # حذف النسخ الموزعة
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        try:
            # حذف الصورة من المصدر + أمر الحذف
            await message.reply_to_message.delete()
            await message.delete()
        except Exception as e:
            logger.error(f"Failed to delete source messages: {e}")
        return

    # 2. التحقق من الرسالة العادية
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # قفل لمنع التكرار (لمدة 60 ثانية)
    lock_key = f"processing_lock:{message.message_id}"
    if await forwarder.redis.get(lock_key): return
    await forwarder.redis.set(lock_key, "1", ex=60)

    text = message.text or message.caption or ""
    # نتجاهل الرسائل الفارغة أو التي تحتوي على معرف القناة (لتجنب تكرار نشر ما نشره البوت)
    if not text or settings.CHANNEL_HANDLE in text: return

    logger.info("🎨 Starting Cinematic Hybrid Design...")
    
    # 3. توليد الخلفية (AI - Flux Schnell)
    # نطلب خلفية فقط، التكلفة منخفضة جداً
    bg_url = await fal_designer.generate_background(text)
    
    # 4. التصميم والدمج (Code - Playwright)
    try:
        # دمج النص العربي فوق الخلفية بتصميم سينمائي
        image_path = await image_gen.render(text, message.message_id, bg_url)
        
        # تجهيز الكابشن (مقتطف من النص)
        lines = [line for line in text.split('\n') if line.strip()]
        excerpt = lines[0] if lines else text[:50]
        if len(excerpt) > 60: excerpt = excerpt[:57] + "..."
        
        final_caption = f"❝ {excerpt}\n\n💎 {settings.CHANNEL_HANDLE}"

        # 5. الإرسال للقناة المصدر
        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=final_caption
            )
        
        # تسجيل الرسالة (مهم للحذف لاحقاً)
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        
        # توزيع الصورة للمشتركين
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        # تنظيف الملفات المؤقتة
        os.remove(image_path)
            
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        # في حال الفشل التام (نادر)، ننشر النص كما هو لضمان وصول المحتوى
        await forwarder.broadcast_message(context.bot, message.message_id)