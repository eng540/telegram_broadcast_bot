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
    """
    معالج ذكي يدعم:
    1. النشر الجديد.
    2. الحذف عبر التعديل (Smart Delete).
    3. الحذف عبر الأمر /del.
    """
    
    # 1. التحقق من المصدر
    if update.effective_chat.id != settings.MASTER_SOURCE_ID:
        return
    
    # التقاط الرسالة (سواء كانت جديدة أو معدلة)
    message = update.channel_post or update.edited_channel_post
    is_edit = update.edited_channel_post is not None
    
    if not message: return

    # --- 🔥 الميزة الجديدة: الحذف عبر التعديل ---
    # إذا قام المشرف بتعديل الرسالة وكتب فيها "حذف" أو "x"
    if is_edit:
        text = message.text or message.caption or ""
        if text.strip().lower() in ["حذف", "x", "delete", "."]:
            logger.info(f"🗑️ Smart Delete triggered for msg: {message.message_id}")
            
            # 1. حذف النسخ الموزعة عند الناس
            await forwarder.delete_broadcast(context.bot, message.message_id)
            
            # 2. حذف الرسالة الأصلية من القناة (تنظيف)
            try: await message.delete()
            except: pass
            
            return # انتهى العمل
        else:
            # إذا كان تعديلاً عادياً (تصحيح إملائي)، نتجاهله حالياً
            # لأن تعديل الصور يتطلب إعادة إرسال، وهو مزعج للمشتركين
            return

    # --- بقية الكود (النشر العادي وأمر /del) ---
    
    # تجاهل رسائل البوت نفسه
    if message.from_user and message.from_user.id == context.bot.id: return
    
    # فلترة الإعلانات
    if FilterService.is_ad(message): return
    
    # معالجة أمر الحذف التقليدي (/del) - (احتياطي)
    if message.reply_to_message and message.text and message.text.strip() == "/del":
        target_msg_id = message.reply_to_message.message_id
        logger.info(f"🗑️ Command /del received for msg: {target_msg_id}")
        try: await message.reply_to_message.delete()
        except: pass
        try: await message.delete()
        except: pass
        await forwarder.delete_broadcast(context.bot, target_msg_id)
        return
    
    # النشر العادي (للمنشورات الجديدة فقط)
    if not is_edit:
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