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
    """معالجة المنشورات من القناة المصدر"""
    
    # 1. التحقق من المصدر
    if update.effective_chat.id != settings.MASTER_SOURCE_ID:
        return
    
    # 2. الحصول على الرسالة
    message = update.channel_post or update.edited_channel_post
    is_edit = update.edited_channel_post is not None
    
    # 3. تجاهل رسائل البوت نفسه
    if not message or (message.from_user and message.from_user.id == context.bot.id):
        return
    
    # 4. فلترة الإعلانات
    if FilterService.is_ad(message):
        return
    
    # 5. معالجة أمر الحذف (/del) - فقط للنشرات العادية
    if not is_edit and message.reply_to_message and message.text and message.text.strip() == "/del":
        target_msg_id = message.reply_to_message.message_id
        logger.info(f"🗑️ Delete command received for msg: {target_msg_id}")
        
        try:
            # حذف الرسالة الأصلية من القناة
            await message.reply_to_message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete original message: {e}")
        
        try:
            # حذف أمر /del نفسه
            await message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete /del command: {e}")
        
        # حذف النسخ الموزعة
        await forwarder.delete_broadcast(context.bot, target_msg_id)
        return
    
    # 6. تجاهل التعديلات للمحافظة على البساطة حالياً
    if is_edit:
        logger.info(f"📝 Edit detected for msg {message.message_id}, ignoring for now")
        return
    
    # 7. النشر العادي (كما هو)
    is_text = (message.text is not None) and (not message.photo) and (not message.video)
    text = message.text or ""

    if is_text and 5 < len(text) < 5000:
        try:
            path = await image_gen.render(text, message.message_id)
            caption = text.split('\n')[0][:97] + "..."
            
            with open(path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=caption,
                    reply_to_message_id=message.message_id
                )
            
            await forwarder.broadcast_message(context.bot, sent.message_id)
            os.remove(path)
            
        except Exception as e:
            logger.error(f"Art Error: {e}")
            await forwarder.broadcast_message(context.bot, message.message_id)
    else:
        await forwarder.broadcast_message(context.bot, message.message_id)