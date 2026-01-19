import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator

logger = logging.getLogger(__name__)
forwarder = ForwarderService()
image_gen = ImageGenerator()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != settings.MASTER_SOURCE_ID: return
    
    message = update.channel_post
    if not message or (message.from_user and message.from_user.id == context.bot.id): return
    if FilterService.is_ad(message): return

    is_text = (message.text is not None) and (not message.photo)
    text = message.text or ""

    if is_text and 5 < len(text) < 3000:
        try:
            image_path = await image_gen.render(text, message.message_id)
            caption = text.split('\n')[0][:97] + "..."
            
            with open(image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=caption,
                    reply_to_message_id=message.message_id
                )
            
            await forwarder.broadcast_message(context.bot, sent.message_id)
            os.remove(image_path)
        except Exception as e:
            logger.error(f"Art Error: {e}")
            await forwarder.broadcast_message(context.bot, message.message_id)
    else:
        await forwarder.broadcast_message(context.bot, message.message_id)