import logging
import os
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

    # قفل التكرار
    lock_key = f"processing_lock:{message.message_id}"
    if await forwarder.redis.get(lock_key): return
    await forwarder.redis.set(lock_key, "1", ex=60)

    # معالجة الحذف
    if message.reply_to_message and message.text == "/del":
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        try:
            await message.reply_to_message.delete()
            await message.delete()
        except: pass
        return

    text = message.text or message.caption or ""
    if not text or settings.CHANNEL_HANDLE in text: return

    logger.info("🎨 Starting Budget-Friendly Design...")
    
    # 1. توليد خلفية رخيصة وسريعة (Flux Schnell)
    bg_url = await fal_designer.generate_background(text)
    
    # 2. الكتابة بالكود (مجاني واحترافي)
    try:
        image_path = await image_gen.render(text, message.message_id, bg_url)
        
        # تجهيز الكابشن
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