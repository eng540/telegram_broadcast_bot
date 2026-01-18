import logging
import os
from telegram import Update, ChatMember
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, CommandHandler, filters
from sqlalchemy import select, func, delete
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import Subscriber
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()
image_gen = ImageGenerator()

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                try: await context.bot.send_message(chat_id, "🕊️ وصل الزاجل!\nتم تفعيل خدمة البطاقات الأدبية.")
                except: pass
    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message: return
        
        # 1. الفلترة
        if FilterService.is_ad(message):
            return
            
        # 2. منطق تحويل النص إلى صورة
        # الشروط: نص موجود + لا يوجد ميديا + الطول مناسب (بين 10 و 400 حرف)
        is_text_only = (message.text is not None) and (not message.photo) and (not message.video)
        text_content = message.text or ""
        
        if is_text_only and 10 < len(text_content) < 400:
            logger.info(f"🎨 Generating Art Card for message {message.message_id}")
            try:
                # توليد الصورة باستخدام الكلاس الجديد
                image_path = image_gen.create_card(text_content, message.message_id)
                
                # تجهيز الكابشن (أول 100 حرف)
                caption_part = text_content[:100] + "..." if len(text_content) > 100 else text_content
                
                # إرسال الصورة
                await forwarder.broadcast_image(context.bot, image_path, caption_part, message.message_id)
                
            except Exception as e:
                logger.error(f"⚠️ Failed to generate image: {e}")
                # في حال الفشل، نرسل النص العادي كخطة بديلة
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)
        else:
            # الرسائل الطويلة أو الفيديوهات
            await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Subscriber))
    await update.message.reply_text(f"📊 المشتركين النشطين: {count}")

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready & Image Generator Loaded.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()