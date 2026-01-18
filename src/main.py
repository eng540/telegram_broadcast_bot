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

# إعداد السجلات (تفعيل المستوى DEBUG لرؤية كل التفاصيل)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
                logger.info(f"➕ New Subscriber: {chat_id}")
    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()
            logger.info(f"➖ Subscriber Left: {chat_id}")

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    نسخة التشخيص: ستخبرنا أين تتوقف الرسالة بالضبط
    """
    # 1. التحقق من المصدر
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message: 
            return

        logger.info(f"📩 RECEIVED POST: ID={message.message_id} | Type={'Text' if message.text else 'Media'}")

        # 2. الفلترة
        if FilterService.is_ad(message):
            logger.warning(f"🚫 BLOCKED BY FILTER: ID={message.message_id}")
            return
        
        logger.info("✅ Passed Ad Filter.")

        # 3. تحليل المحتوى
        is_text_only = (message.text is not None) and (not message.photo) and (not message.video)
        text_content = message.text or ""
        
        logger.info(f"🔍 CONTENT CHECK: TextOnly={is_text_only}, Length={len(text_content)}")

        if is_text_only and 5 < len(text_content) < 450:
            logger.info("🎨 Starting Image Rendering...")
            try:
                # استدعاء المحرك
                image_path = await image_gen.render(text_content, message.message_id)
                logger.info(f"✅ Render Success: {image_path}")
                
                caption_part = text_content.split('\n')[0][:97] + "..." if len(text_content) > 100 else text_content.split('\n')[0]
                
                logger.info("🚀 Broadcasting Image...")
                await forwarder.broadcast_image(context.bot, image_path, caption_part, message.message_id)
                
            except Exception as e:
                logger.error(f"❌ RENDER ERROR: {e}", exc_info=True)
                logger.info("🔄 Falling back to text broadcast.")
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)
        else:
            logger.info("📢 Broadcasting RAW message (Not suitable for card).")
            await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)
    else:
        # رسالة من مصدر غير معروف (للتأكد فقط)
        logger.info(f"⚠️ Ignored message from wrong chat: {update.effective_chat.id}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Subscriber))
    await update.message.reply_text(f"Users: {count}")

async def post_init(app: Application):
    await init_db()
    logger.info(f"🛡️ System Ready. Watching: {settings.MASTER_SOURCE_ID}")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()