import logging
import os
import asyncio
from telegram import Update, ChatMember
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, CommandHandler, filters
from sqlalchemy import select, func, delete
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

forwarder = ForwarderService()
image_gen = ImageGenerator()

# --- دالة مساعدة لتسجيل المستخدم (المالك) ---
async def ensure_user_exists(session, user):
    """يتأكد من أن هذا المستخدم مسجل في النظام"""
    if not user: return None
    
    db_user = await session.get(BotUser, user.id)
    if not db_user:
        new_user = BotUser(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username
        )
        session.add(new_user)
        # Flush مهم للحصول على ID قبل الـ Commit النهائي
        await session.flush() 
        logger.info(f"👤 Registered New Owner: {user.first_name} ({user.id})")
    return user.id

# --- 1. التعامل مع الأفراد (/start) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if update.effective_chat.type != ChatType.PRIVATE:
        return

    async with AsyncSessionLocal() as session:
        await ensure_user_exists(session, user)
        await session.commit()

    welcome_text = (
        f"أهلاً بك يا *{user.first_name}* 🌹\n\n"
        "أنا **زاجل**، بوت الأدب العربي.\n"
        "تم تسجيلك في القائمة الخاصة، وستصلك الروائع يومياً.\n\n"
        "💡 **هل لديك قناة أو مجموعة؟**\n"
        "أضفني مشرفاً فيها، وسأقوم بتغذيتها بالمحتوى الراقي تلقائياً."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

# --- 2. متابعة القنوات والمجموعات (الذكاء هنا) ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    
    new_state = result.new_chat_member
    chat = result.chat
    # الشخص الذي قام بالإضافة (المالك/المشرف)
    added_by_user = result.from_user 
    
    # البوت أصبح عضواً أو مشرفاً
    if new_state.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        
        async with AsyncSessionLocal() as session:
            # 1. تسجيل المالك أولاً
            owner_id = await ensure_user_exists(session, added_by_user)
            
            # 2. تحديد نوع الإضافة (قناة أم مجموعة)
            if chat.type == ChatType.CHANNEL:
                existing = await session.get(TelegramChannel, chat.id)
                if not existing:
                    new_channel = TelegramChannel(
                        chat_id=chat.id, 
                        title=chat.title,
                        added_by_id=owner_id # ربط القناة بالمالك
                    )
                    session.add(new_channel)
                    logger.info(f"📢 New Channel Linked: {chat.title} (Owner: {added_by_user.first_name})")

            elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                existing = await session.get(TelegramGroup, chat.id)
                if not existing:
                    new_group = TelegramGroup(
                        chat_id=chat.id, 
                        title=chat.title,
                        added_by_id=owner_id # ربط المجموعة بالمالك
                    )
                    session.add(new_group)
                    logger.info(f"🏘️ New Group Linked: {chat.title} (Owner: {added_by_user.first_name})")
                    try: await context.bot.send_message(chat.id, "🕊️ وصل الزاجل!\nتم تفعيل الخدمة.")
                    except: pass
            
            await session.commit()

    # البوت طُرد
    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            if chat.type == ChatType.CHANNEL:
                await session.execute(delete(TelegramChannel).where(TelegramChannel.chat_id == chat.id))
            else:
                await session.execute(delete(TelegramGroup).where(TelegramGroup.chat_id == chat.id))
            await session.commit()

# --- 3. النشر (لم يتغير المنطق، فقط الجودة) ---
async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message or (message.from_user and message.from_user.id == context.bot.id): return
        if FilterService.is_ad(message): return

        is_text_only = (message.text is not None) and (not message.photo) and (not message.video)
        text_content = message.text or ""
        
        if is_text_only and 5 < len(text_content) < 2000:
            try:
                image_path = await image_gen.render(text_content, message.message_id)
                caption = text_content.split('\n')[0][:97] + "..." if len(text_content) > 100 else text_content.split('\n')[0]
                
                with open(image_path, 'rb') as f:
                    sent = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID, photo=f, caption=caption, reply_to_message_id=message.message_id
                    )
                
                await forwarder.broadcast_message(context.bot, sent.message_id)
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Art Failed: {e}")
                await forwarder.broadcast_message(context.bot, message.message_id)
        else:
            await forwarder.broadcast_message(context.bot, message.message_id)

# --- 4. إحصائيات الأثرياء (Data-Rich Stats) ---
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    
    async with AsyncSessionLocal() as session:
        users = await session.scalar(select(func.count()).select_from(BotUser))
        channels = await session.scalar(select(func.count()).select_from(TelegramChannel))
        groups = await session.scalar(select(func.count()).select_from(TelegramGroup))
        
    report = (
        f"📊 **تقرير الأصول الرقمية**\n\n"
        f"👤 **قاعدة الأفراد:** `{users}`\n"
        f"📢 **القنوات الشريكة:** `{channels}`\n"
        f"🏘️ **المجموعات المستضيفة:** `{groups}`\n\n"
        f"💎 **إجمالي نقاط الوصول:** `{users + channels + groups}` كيان"
    )
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready. Enterprise DB Structure Active.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()