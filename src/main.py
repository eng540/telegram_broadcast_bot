import logging
from telegram import Update, ChatMember
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, filters
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import Subscriber
from src.services.forwarder import ForwarderService
from sqlalchemy import delete

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

forwarder = ForwarderService()

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return

    new_state = result.new_chat_member
    chat_id = result.chat.id

    if new_state.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        async with AsyncSessionLocal() as session:
            existing = await session.get(Subscriber, chat_id)
            if not existing:
                session.add(Subscriber(chat_id=chat_id))
                await session.commit()

    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        await forwarder.broadcast_message(
            context.bot,
            settings.MASTER_SOURCE_ID,
            update.channel_post.message_id
        )

async def post_init(app: Application):
    await init_db()

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(
        filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST,
        handle_source_post
    ))
    application.run_polling()

if __name__ == "__main__":
    main()
