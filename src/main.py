import logging
from telegram import Update, BotCommand
from telegram.ext import Application, ChatMemberHandler, CommandHandler, MessageHandler, filters
from src.config import settings
from src.database import init_db
from src.handlers.users import start_command, handle_private_design
from src.handlers.groups import track_chats
from src.handlers.channel import handle_source_post
from src.handlers.admin import stats_command

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def post_init(app: Application):
    await init_db()
    await app.bot.set_my_commands([BotCommand("start", "البدء"), BotCommand("help", "مساعدة")])
    logger.info("🛡️ System Ready. Production Mode 1.0")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_private_design))
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()