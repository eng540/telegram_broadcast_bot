import logging
import os
import asyncio
from telegram import Update, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, CommandHandler, filters
from sqlalchemy import select, func, update, delete
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

forwarder = ForwarderService()
image_gen = ImageGenerator()

# --- 🔔 خدمة إشعار المدير (عين الصقر) ---
async def notify_admin(bot, text):
    """إرسال تقرير فوري للمدير عند حدوث نشاط جديد"""
    try:
        await bot.send_message(
            chat_id=settings.ADMIN_ID,
            text=f"🔔 **إشعار نشاط جديد:**\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.warning(f"Failed to notify admin: {e}")

# --- 👤 إدارة المستخدمين ---
async def ensure_user_exists(session, user, bot):
    """تسجيل المستخدم وإشعار المدير"""
    if not user: return None
    
    result = await session.execute(select(BotUser).where(BotUser.user_id == user.id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        new_user = BotUser(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username,
            is_active=True
        )
        session.add(new_user)
        await session.flush()
        logger.info(f"👤 New User: {user.first_name}")
        # إشعار المدير
        await notify_admin(bot, f"👤 **مشترك جديد:** {user.first_name}\n🆔 `{user.id}`")
    else:
        if not db_user.is_active:
            db_user.is_active = True
            await notify_admin(bot, f"♻️ **عودة مشترك:** {user.first_name}")
        
        # تحديث البيانات
        if db_user.first_name != user.first_name: db_user.first_name = user.first_name
        if db_user.username != user.username: db_user.username = user.username
        await session.flush()

    return user.id

# --- 👋 أمر البداية (الواجهة الاحترافية) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != ChatType.PRIVATE: return

    async with AsyncSessionLocal() as session:
        await ensure_user_exists(session, user, context.bot)
        await session.commit()

    # --- التصميم الاحترافي للرسالة ---
    welcome_text = (
        f"مرحباً بك يا *{user.first_name}* 👋\n\n"
        "أنا **زاجل**، رفيقك الفني لنقل روائع الأدب العربي.\n"
        "سأقوم بصياغة النصوص الشعرية في لوحات فنية وأرسلها إليك يومياً.\n\n"
        "👇 **اختر ما تريد من الأسفل:**"
    )

    # الأزرار الشفافة (Inline Buttons)
    keyboard = [
        [
            InlineKeyboardButton("📢 القناة الرسمية (المصدر)", url="https://t.me/Rwaea3")
        ],
        [
            InlineKeyboardButton("➕ أضفني لمجموعتك", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# --- 🏘️ متابعة القنوات والمجموعات ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    
    new_state = result.new_chat_member
    chat = result.chat
    added_by = result.from_user 
    
    async with AsyncSessionLocal() as session:
        if new_state.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            # تسجيل المالك
            owner_id = await ensure_user_exists(session, added_by, context.bot)
            
            # القنوات
            if chat.type == ChatType.CHANNEL:
                res = await session.execute(select(TelegramChannel).where(TelegramChannel.chat_id == chat.id))
                if not res.scalar_one_or_none():
                    session.add(TelegramChannel(chat_id=chat.id, title=chat.title, added_by_id=owner_id, is_active=True))
                    await notify_admin(context.bot, f"📢 **قناة جديدة:** {chat.title}\nبواسطة: {added_by.first_name}")

            # المجموعات
            elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                res = await session.execute(select(TelegramGroup).where(TelegramGroup.chat_id == chat.id))
                if not res.scalar_one_or_none():
                    session.add(TelegramGroup(chat_id=chat.id, title=chat.title, added_by_id=owner_id, is_active=True))
                    await notify_admin(context.bot, f"🏘️ **مجموعة جديدة:** {chat.title}\nبواسطة: {added_by.first_name}")
                    try: await context.bot.send_message(chat.id, "🕊️ وصل الزاجل!\nتم تفعيل خدمة البطاقات الأدبية.")
                    except: pass
        
        elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
            # تعطيل (Soft Delete)
            model = TelegramChannel if chat.type == ChatType.CHANNEL else TelegramGroup
            await session.execute(update(model).where(model.chat_id == chat.id).values(is_active=False))
            logger.info(f"💤 Deactivated: {chat.title}")

        await session.commit()

# --- 🎨 النشر الذكي ---
async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message or (message.from_user and message.from_user.id == context.bot.id): return
        if FilterService.is_ad(message): return

        is_text = (message.text is not None) and (not message.photo) and (not message.video)
        text = message.text or ""
        
        if is_text and 5 < len(text) < 3000:
            try:
                # 1. تصميم
                image_path = await image_gen.render(text, message.message_id)
                caption = text.split('\n')[0][:97] + "..." if len(text) > 100 else text.split('\n')[0]
                
                # 2. إرسال للقناة
                with open(image_path, 'rb') as f:
                    sent = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID, photo=f, caption=caption, reply_to_message_id=message.message_id
                    )
                
                # 3. توزيع فوري
                await forwarder.broadcast_message(context.bot, sent.message_id)
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Art Error: {e}")
                await forwarder.broadcast_message(context.bot, message.message_id)
        else:
            await forwarder.broadcast_message(context.bot, message.message_id)

# --- 📊 الإحصائيات (للمدير فقط) ---
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    
    async with AsyncSessionLocal() as session:
        users = await session.scalar(select(func.count()).select_from(BotUser).where(BotUser.is_active == True))
        channels = await session.scalar(select(func.count()).select_from(TelegramChannel).where(TelegramChannel.is_active == True))
        groups = await session.scalar(select(func.count()).select_from(TelegramGroup).where(TelegramGroup.is_active == True))
        
    await update.message.reply_text(
        f"📊 **لوحة التحكم الحية**\n"
        f"──────────────\n"
        f"👤 الأفراد: `{users}`\n"
        f"📢 القنوات: `{channels}`\n"
        f"🏘️ المجموعات: `{groups}`\n"
        f"──────────────",
        parse_mode=ParseMode.MARKDOWN
    )

async def post_init(app: Application):
    await init_db()
    
    # إعداد قائمة الأوامر (Menu) لتظهر للمستخدمين
    commands = [
        BotCommand("start", "تفعيل البوت والترحيب"),
        BotCommand("help", "كيفية الاستخدام"),
    ]
    await app.bot.set_my_commands(commands)
    
    logger.info("🛡️ System Ready. Admin Notifications Active.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()