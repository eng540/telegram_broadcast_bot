import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator
from src.services.fal_design import FalDesignService # الاقتصادي
from src.services.google_design import GoogleDesignService # الاحترافي

logger = logging.getLogger(__name__)

forwarder = ForwarderService()
image_gen = ImageGenerator()
fal_designer = FalDesignService()
google_designer = GoogleDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    
    # ---------------------------------------------------------
    # 1. أوامر التحكم اليدوي (PRO / DELETE)
    # ---------------------------------------------------------
    if message and message.reply_to_message and message.text:
        command = message.text.strip().lower()
        
        # حذف
        if command == "/del":
            await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
            try: 
                await message.reply_to_message.delete()
                await message.delete()
            except: pass
            return

        # تصميم احترافي (PRO)
        if command == "/pro":
            original_text = message.reply_to_message.text or message.reply_to_message.caption
            if not original_text: return
            
            logger.info("💎 Manual PRO trigger received.")
            await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
            
            # استخدام محرك جوجل القوي
            image_path = await google_designer.generate_pro_design(original_text, message.message_id)
            
            if image_path:
                with open(image_path, 'rb') as f:
                    sent = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID,
                        photo=f,
                        caption=f"✨ {settings.CHANNEL_HANDLE}"
                    )
                # نوزع النسخة الاحترافية
                await forwarder.broadcast_message(context.bot, sent.message_id)
                # نحذف الطلب والنسخة القديمة (اختياري)
                try: await message.delete()
                except: pass
                os.remove(image_path)
            return

    # ---------------------------------------------------------
    # 2. النشر التلقائي (الاقتصادي)
    # ---------------------------------------------------------
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # قفل التكرار
    lock_key = f"processing_lock:{message.message_id}"
    if await forwarder.redis.get(lock_key): return
    await forwarder.redis.set(lock_key, "1", ex=60)

    text = message.text or message.caption or ""
    if not text or settings.CHANNEL_HANDLE in text: return

    logger.info("🎨 Starting Economy Design...")
    
    # خلفية رخيصة (Flux)
    bg_data = await fal_designer.generate_background_b64(text)
    
    # دمج بالكود (مجاني)
    try:
        image_path = await image_gen.render(text, message.message_id, bg_data)
        
        lines = [line for line in text.split('\n') if line.strip()]
        excerpt = lines[0][:50] + "..." if lines else ""
        caption = f"❝ {excerpt}\n\n💎 {settings.CHANNEL_HANDLE}"

        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=caption
            )
        
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        os.remove(image_path)
            
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        await forwarder.broadcast_message(context.bot, message.message_id)