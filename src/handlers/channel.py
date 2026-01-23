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

forwarder = ForwarderService()
image_gen = ImageGenerator()
fal_designer = FalDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # --- إصلاح التكرار ---
    # نستخدم Redis لقفل الرسالة فوراً قبل البدء بالعمل
    lock_key = f"processing_lock:{message.message_id}"
    is_locked = await forwarder.redis.get(lock_key)
    if is_locked: 
        logger.info(f"🔒 Message {message.message_id} is already being processed.")
        return
    
    # نضع القفل لمدة 60 ثانية
    await forwarder.redis.set(lock_key, "1", ex=60)

    # --- إصلاح الحذف ---
    # إذا كانت الرسالة أمر حذف
    if message.reply_to_message and message.text == "/del":
        logger.info("🗑️ Delete command received.")
        # نحذف الرسالة التي تم الرد عليها (الصورة) من جميع القنوات
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        try:
            await message.reply_to_message.delete() # حذف الصورة من المصدر
            await message.delete() # حذف أمر /del
        except Exception as e:
            logger.error(f"Failed to delete source messages: {e}")
        return

    # --- المعالجة ---
    text = message.text or message.caption or ""
    if not text: return

    # إذا كانت الرسالة من البوت نفسه (تحتوي على التوقيع)، نتجاهلها
    if settings.CHANNEL_HANDLE in text: return

    logger.info("🎨 Starting Hybrid Design...")
    
    # 1. جلب الخلفية من Fal
    bg_url = await fal_designer.generate_background(text)
    
    # 2. دمج النص (سواء نجح Fal أو فشل، سنستخدم الخلفية الافتراضية في حال الفشل)
    try:
        image_path = await image_gen.render(text, message.message_id, bg_url)
        
        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=f"✨ {settings.CHANNEL_HANDLE}"
            )
        
        # تسجيل الرسالة الجديدة في السجل (مهم للحذف لاحقاً)
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        
        # توزيع
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        os.remove(image_path)
        
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        # في حال الفشل التام، ننشر النص
        await forwarder.broadcast_message(context.bot, message.message_id)