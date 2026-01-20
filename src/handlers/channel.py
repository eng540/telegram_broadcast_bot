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

# 🛡️ نظام الحماية الذاتية (ذاكرة مؤقتة)
# يخزن أرقام الرسائل التي ولدها البوت لكي لا يعيد معالجتها
_self_generated_ids = set()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج القناة المصدر (النسخة المصححة والمحمية)
    """
    if update.effective_chat.id != settings.MASTER_SOURCE_ID: return
    
    message = update.channel_post or update.edited_channel_post
    is_edit = update.edited_channel_post is not None
    
    if not message: return

    # 1. 🛡️ الحماية الذاتية: هل هذه الرسالة من صنعي؟
    # نتجاهلها فوراً لمنع الحلقات اللانهائية
    if message.message_id in _self_generated_ids:
        return

    # تنظيف الذاكرة إذا كبرت جداً
    if len(_self_generated_ids) > 1000:
        _self_generated_ids.clear()

    # 2. 🛡️ حماية إضافية: فحص الكابشن (للتأكد)
    if message.photo:
        caption = message.caption or ""
        if settings.CHANNEL_HANDLE in caption:
            return

    # 3. ✏️ معالجة التعديلات (الحذف أو التحديث)
    if is_edit:
        text = message.text or message.caption or ""
        # أ) أمر الحذف
        if text.strip().lower() in ["حذف", "x", "delete", "."]:
            logger.info(f"🗑️ Smart Delete triggered: {message.message_id}")
            await forwarder.delete_broadcast(context.bot, message.message_id)
            try: await message.delete()
            except: pass
            return
        
        # ب) تعديل المحتوى (نسمح به الآن لإنشاء بطاقة جديدة)
        logger.info(f"✏️ Edit detected, regenerating art for: {message.message_id}")
        # نكمل الكود للأسفل ليتم التصميم من جديد...

    # 4. الفلترة الأمنية
    if message.from_user and message.from_user.id == context.bot.id: return
    if FilterService.is_ad(message): return

    # 5. المنطق الرئيسي (التصميم والنشر)
    is_text = (message.text is not None) and (not message.photo) and (not message.video)
    text = message.text or ""

    # أ) مسار النصوص (تصميم)
    if is_text and 5 < len(text) < 5000:
        try:
            # تصميم الصورة
            image_path = await image_gen.render(text, message.message_id)
            
            # استخراج المقتطف للكابشن
            lines = [line for line in text.split('\n') if line.strip()]
            excerpt = lines[0] if lines else "مقتطف"
            if len(excerpt) > 60: excerpt = excerpt[:57] + "..."
            
            final_caption = content.get("art.caption", excerpt=excerpt)
            
            # الإرسال للقناة (بدون Reply لتجنب التكرار)
            with open(image_path, 'rb') as f:
                sent = await context.bot.send_photo(
                    chat_id=settings.MASTER_SOURCE_ID,
                    photo=f,
                    caption=final_caption
                    # ❌ تم حذف reply_to_message_id لمنع الازدواجية
                )
            
            # تسجيل الرسالة الجديدة في الحماية الذاتية
            _self_generated_ids.add(sent.message_id)
            
            # التوزيع الفوري
            try:
                await forwarder.broadcast_message(context.bot, sent.message_id)
            except Exception as e:
                logger.error(f"Broadcast Error: {e}")
            
            # تنظيف
            os.remove(image_path)
            
            # (اختياري) حذف النص الأصلي لتبقى القناة نظيفة (تحتوي صوراً فقط)
            # try: await message.delete()
            # except: pass
            
        except Exception as e:
            logger.error(f"Art Generation Failed: {e}")
            # في حال الفشل، نوزع النص
            await forwarder.broadcast_message(context.bot, message.message_id)

    # ب) مسار الميديا الجاهزة
    else:
        await forwarder.broadcast_message(context.bot, message.message_id)