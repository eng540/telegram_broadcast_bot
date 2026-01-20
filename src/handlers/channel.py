import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator
from src.services.content_manager import content

logger = logging.getLogger(__name__)
forwarder = ForwarderService()
image_gen = ImageGenerator()

_self_generated_ids = set()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != settings.MASTER_SOURCE_ID: return
    
    message = update.channel_post or update.edited_channel_post
    is_edit = update.edited_channel_post is not None
    if not message: return

    # 1. منع التكرار (الذاكرة)
    if message.message_id in _self_generated_ids: return
    if len(_self_generated_ids) > 1000: _self_generated_ids.clear()

    # 2. منع التكرار (الكابشن)
    if message.photo:
        caption = message.caption or ""
        if settings.CHANNEL_HANDLE.replace("@", "") in caption: return

    # 3. الحذف الذكي
    if is_edit:
        text = message.text or message.caption or ""
        if text.strip().lower() in ["حذف", "x", "delete", "."]:
            logger.info(f"🗑️ Smart Delete: {message.message_id}")
            await forwarder.delete_broadcast(context.bot, message.message_id)
            try: await message.delete()
            except: pass
            return
        else: return

    if message.reply_to_message and message.text == "/del":
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        try: 
            await message.reply_to_message.delete()
            await message.delete()
        except: pass
        return

    # 4. النشر
    if message.from_user and message.from_user.id == context.bot.id: return
    if FilterService.is_ad(message): return

    is_text = (message.text is not None) and (not message.photo)
    text = message.text or ""

    if is_text and 5 < len(text) < 5000:
        try:
            image_path = await image_gen.render(text, message.message_id)
            
            lines = [line for line in text.split('\n') if line.strip()]
            excerpt = lines[0][:57] + "..." if lines and len(lines[0]) > 60 else (lines[0] if lines else "")
            final_caption = content.get("art.caption", excerpt=excerpt)
            
            with open(image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=final_caption
                )
            
            _self_generated_ids.add(sent.message_id)
            await forwarder.broadcast_message(context.bot, sent.message_id)
            os.remove(image_path)
        except Exception as e:
            logger.error(f"Art Failed: {e}")
            await forwarder.broadcast_message(context.bot, message.message_id)
    else:
        await forwarder.broadcast_message(context.bot, message.message_id)