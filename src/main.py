import logging
import os
import asyncio
from telegram import Update, ChatMember
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, CommandHandler, filters
from sqlalchemy import select, func, delete
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import Subscriber
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

forwarder = ForwarderService()
image_gen = ImageGenerator()

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """متابعة المشتركين"""
    result = update.my_chat_member
    if not result: return
    new_state = result.new_chat_member
    chat_id = result.chat.id
    
    if new_state.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        async with AsyncSessionLocal() as session:
            existing = await session.get(Subscriber, chat_id)
            if not existing:
                session.add(Subscriber(chat_id=chat_id))
                await session.commit()
                try: await context.bot.send_message(chat_id, "🕊️ وصل الزاجل!\nتم تفعيل الخدمة.")
                except: pass
    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    المنطق المباشر:
    1. نص -> تصميم -> إرسال للقناة -> (نسخ المعرف) -> توزيع فوري للمشتركين.
    2. ميديا -> توزيع فوري.
    """
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message: return
        
        # تجاهل الرسائل التي يرسلها البوت بنفسه لتجنب التكرار
        # (رغم أن نظام Redis يحمينا، لكن زيادة حرص)
        if message.from_user and message.from_user.id == context.bot.id:
            return

        # 1. الفلترة
        if FilterService.is_ad(message):
            return
            
        # 2. هل الرسالة نصية تحتاج لتصميم؟
        is_text_only = (message.text is not None) and (not message.photo) and (not message.video)
        text_content = message.text or ""
        
        if is_text_only and 5 < len(text_content) < 2000: # زدنا الحد لدعم القصائد الطويلة
            logger.info(f"🎨 Processing Art for: {message.message_id}")
            try:
                # أ) التصميم
                image_path = await image_gen.render(text_content, message.message_id)
                
                # ب) تجهيز الكابشن
                caption_part = text_content.split('\n')[0]
                if len(caption_part) > 100: caption_part = caption_part[:97] + "..."
                
                # ج) الإرسال للقناة المصدر (والاحتفاظ بالنتيجة في متغير)
                with open(image_path, 'rb') as f:
                    sent_message = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID,
                        photo=f,
                        caption=caption_part,
                        reply_to_message_id=message.message_id 
                    )
                
                logger.info(f"✅ Posted to Channel. New ID: {sent_message.message_id}")
                
                # د) التوزيع الفوري للمشتركين (بدون انتظار إشعار)
                # نستخدم ID الرسالة الجديدة (sent_message) التي تحتوي على الصورة
                logger.info("🚀 Triggering Direct Broadcast...")
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, sent_message.message_id)
                
                # هـ) التنظيف
                os.remove(image_path)
                return

            except Exception as e:
                logger.error(f"⚠️ Art Failed: {e}", exc_info=True)
                # في حال الفشل، نوزع النص الأصلي
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)
        
        else:
            # 3. ميديا جاهزة (فيديو، صوت، أو صورة من المشرف)
            logger.info(f"📢 Broadcasting Raw Media: {message.message_id}")
            await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Subscriber))
    await update.message.reply_text(f"📊 المشتركين: {count}")

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready. Direct Broadcast Mode.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()