import logging
import os
import asyncio
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
    
    # 1. معالجة أمر الحذف (الأولوية القصوى)
    # إذا كانت الرسالة رداً على رسالة أخرى، والنص هو /del
    if message and message.reply_to_message and message.text and message.text.strip() == "/del":
        logger.info("🗑️ Delete command received.")
        
        # نحذف الرسالة التي تم الرد عليها (الصورة) من جميع القنوات
        # ملاحظة: يجب أن تكون الرسالة الأصلية مسجلة في قاعدة البيانات (BroadcastLog)
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        
        try:
            # نحذف الصورة من القناة المصدر
            await message.reply_to_message.delete()
            # نحذف أمر /del نفسه
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
    # نتجاهل الرسائل الفارغة أو التي تحتوي على معرف القناة (لتجنب التكرار)
    if not text or settings.CHANNEL_HANDLE in text: return

    logger.info("🎨 Designing Card...")
    
    # 3. توليد الخلفية (AI)
    bg_path = await ai_bg.generate(text)
    
    # 4. التصميم والدمج
    try:
        image_path = await image_gen.render(text, message.message_id, bg_path)
        
        # --- تجهيز الكابشن (الاقتباس) ---
        # نأخذ أول سطرين أو أول 100 حرف
        lines = [line for line in text.split('\n') if line.strip()]
        excerpt = lines[0] if lines else text[:50]
        if len(excerpt) > 60: excerpt = excerpt[:57] + "..."
        
        # الكابشن النهائي
        final_caption = f"❝ {excerpt}\n\n💎 {settings.CHANNEL_HANDLE}"

        # 5. الإرسال
        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=final_caption
            )
        
        # تسجيل الرسالة (مهم جداً لعمل أمر الحذف لاحقاً)
        # نسجل ID الرسالة التي أرسلها البوت (الصورة) وليس النص الأصلي
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        
        # توزيع الصورة للمشتركين
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        # تنظيف
        os.remove(image_path)
        if bg_path and os.path.exists(bg_path):
            os.remove(bg_path)
            
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        # في حال الفشل، ننشر النص كما هو
        await forwarder.broadcast_message(context.bot, message.message_id)