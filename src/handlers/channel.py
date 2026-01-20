#--- START OF FILE telegram_broadcast_bot-main/src/handlers/channel.py ---

import logging
import os
import asyncio
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

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != settings.MASTER_SOURCE_ID: return
    
    message = update.channel_post or update.edited_channel_post
    is_edit = update.edited_channel_post is not None
    
    if not message: return

    # --- 1. الحماية من التكرار ---
    is_self_generated = await forwarder.redis.exists(f"bot_gen:{message.message_id}")
    if is_self_generated: return

    if message.sender_chat and message.sender_chat.id == settings.MASTER_SOURCE_ID:
        if message.photo and message.caption and settings.CHANNEL_HANDLE.replace("@", "") in message.caption:
            return

    # --- 2. معالجة الحذف ---
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

    # --- 3. الفلترة ---
    if FilterService.is_ad(message): return

    # --- 4. النشر والتصميم ---
    is_text = (message.text is not None) and (not message.photo) and (not message.video)
    text = message.text or ""

    if is_text:
        if 5 < len(text) < 5000:
            # متغير لتتبع هل نجحنا في إرسال الصورة للمصدر أم لا
            card_sent_to_source = False
            
            try:
                # 1. توليد الصورة
                image_path = await image_gen.render(text, message.message_id)
                
                # 2. تجهيز الكابشن
                lines = [line for line in text.split('\n') if line.strip()]
                excerpt = lines[0][:57] + "..." if lines and len(lines[0]) > 60 else (lines[0] if lines else "")
                final_caption = content.get("art.caption", excerpt=excerpt)
                
                # 3. إرسال البطاقة للقناة المصدر
                with open(image_path, 'rb') as f:
                    sent = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID,
                        photo=f,
                        caption=final_caption
                    )
                
                # ✅ علامة النجاح: الصورة وصلت للمصدر
                card_sent_to_source = True
                
                # 4. تسجيل البطاقة
                await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
                
                # تنظيف الملف
                os.remove(image_path)

                # 5. توزيع البطاقة (في كتلة try منفصلة)
                # نفصل التوزيع عن التوليد، حتى لو فشل التوزيع لا نرسل النص
                try:
                    await forwarder.broadcast_message(context.bot, sent.message_id)
                except Exception as broadcast_error:
                    logger.error(f"⚠️ Broadcast failed partially: {broadcast_error}")
                
                # ✅ خروج نهائي: لا نرسل النص أبداً
                return 

            except Exception as e:
                # إذا وصلنا لهنا، فهذا يعني أن الخطأ حدث *قبل* إرسال الصورة للمصدر
                # أو أننا لم ننجح في توليدها أصلاً.
                if card_sent_to_source:
                    # إذا كانت الصورة قد أرسلت للمصدر، فلا داعي لإرسال النص، نكتفي بالخطأ
                    logger.error(f"❌ Error after sending card: {e}")
                    return
                
                logger.error(f"❌ Art Generation Failed: {e}", exc_info=True)
                # هنا فقط (إذا فشل التصميم تماماً) نرسل النص
        
        # Fallback للنصوص الغريبة أو عند فشل التصميم الكلي
        await forwarder.broadcast_message(context.bot, message.message_id)

    else:
        # وسائط أخرى
        await forwarder.broadcast_message(context.bot, message.message_id)