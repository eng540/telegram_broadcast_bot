import logging
from telegram import Update, ChatMember
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, CommandHandler, filters
from sqlalchemy import select, func, delete
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import Subscriber
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """متابعة دخول وخروج البوت من القنوات/المجموعات"""
    result = update.my_chat_member
    if not result: return
    
    new_state = result.new_chat_member
    chat_id = result.chat.id
    chat_name = result.chat.title or result.chat.username or str(chat_id)
    
    if new_state.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        async with AsyncSessionLocal() as session:
            existing = await session.get(Subscriber, chat_id)
            if not existing:
                session.add(Subscriber(chat_id=chat_id))
                await session.commit()
                logger.info(f"➕ New Subscriber: {chat_name} ({chat_id})")
                try: 
                    await context.bot.send_message(chat_id, "🕊️ تم تفعيل خدمة الزاجل بنجاح!")
                except: 
                    pass

    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()
            logger.info(f"➖ Subscriber Left: {chat_name} ({chat_id})")

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة المنشورات القادمة من القناة المصدر"""
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        
        # استخدام خدمة الفلترة
        if FilterService.is_ad(message):
            return
            
        # بدء النشر
        await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر خاص بالمشرف لعرض الإحصائيات"""
    user_id = update.effective_user.id
    if user_id != settings.ADMIN_ID:
        return

    async with AsyncSessionLocal() as session:
        # حساب عدد المشتركين بسرعة
        count = await session.scalar(select(func.count()).select_from(Subscriber))
        
    await update.message.reply_text(f"📊 **إحصائيات الزاجل:**\n\n👥 عدد المشتركين النشطين: `{count}`", parse_mode="Markdown")

async def post_init(app: Application):
    """تهيئة قاعدة البيانات عند التشغيل"""
    await init_db()
    logger.info(f"🛡️ System Ready. Monitoring Source: {settings.MASTER_SOURCE_ID}")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    
    # Handlers
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # رسالة ترحيب بسيطة في الخاص
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.COMMAND, lambda u,c: u.message.reply_text("أهلاً بك في بوت الزاجل للنشر التلقائي.")))
    
    # مراقب القناة المصدر
    application.add_handler(MessageHandler(
        filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, 
        handle_source_post
    ))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()