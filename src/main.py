import logging
import os
import asyncio
from telegram import Update, ChatMember
from telegram.constants import ParseMode
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

# --- ميزة 1: التعامل مع المشتركين الأفراد (Start Command) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    عندما يبدأ مستخدم محادثة خاصة مع البوت:
    1. نحفظه في قاعدة البيانات كمشترك.
    2. نرسل له رسالة ترحيبية وتوجيهية.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id

    # 1. الحفظ في قاعدة البيانات
    async with AsyncSessionLocal() as session:
        existing = await session.get(Subscriber, chat_id)
        if not existing:
            session.add(Subscriber(chat_id=chat_id))
            await session.commit()
            logger.info(f"👤 New Private Subscriber: {user.first_name} ({chat_id})")
        else:
            logger.info(f"👤 Existing User Restarted Bot: {chat_id}")

    # 2. رسالة الترحيب الاحترافية
    welcome_text = (
        f"أهلاً بك يا *{user.first_name}* في رحاب الأدب العربي 🕊️\n\n"
        "أنا **زاجل**، بوت فني مخصص لنقل روائع الكلمة.\n"
        "تم تسجيل اشتراكك بنجاح، وستصلك البطاقات الأدبية المصممة يومياً هنا.\n\n"
        "💎 **مصدرنا الرسمي:**\n"
        "يمكنك متابعة القناة الأم لكل جديد:\n"
        "[اضغط هنا للدخول للقناة](https://t.me/Rwaea3)\n\n"
        "إذا أردت تفعيل الخدمة في مجموعتك، فقط أضفني مشرفاً هناك."
    )
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True # نمنع ظهور معاينة الرابط ليبقى الشكل أنيقاً
    )

# --- ميزة 2: متابعة المجموعات (Chat Member) ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """متابعة دخول وخروج البوت من المجموعات"""
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
                # رسالة ترحيب خاصة بالمجموعات
                try: await context.bot.send_message(chat_id, "🕊️ وصل الزاجل!\nتم تفعيل خدمة البطاقات الأدبية في مجموعتكم.")
                except: pass
    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()

# --- ميزة 3: المعالج الرئيسي للمنشورات ---
async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    المنطق: نص -> تصميم -> نشر للقناة -> توزيع للمشتركين (مجموعات وأفراد)
    """
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message: return
        
        # تجاهل رسائل البوت نفسه
        if message.from_user and message.from_user.id == context.bot.id:
            return

        if FilterService.is_ad(message):
            return
            
        is_text_only = (message.text is not None) and (not message.photo) and (not message.video)
        text_content = message.text or ""
        
        if is_text_only and 5 < len(text_content) < 2000:
            logger.info(f"🎨 Processing Art for: {message.message_id}")
            try:
                # أ) التصميم
                image_path = await image_gen.render(text_content, message.message_id)
                
                # ب) الكابشن
                caption_part = text_content.split('\n')[0]
                if len(caption_part) > 100: caption_part = caption_part[:97] + "..."
                
                # ج) الإرسال للقناة
                with open(image_path, 'rb') as f:
                    sent_message = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID,
                        photo=f,
                        caption=caption_part,
                        reply_to_message_id=message.message_id 
                    )
                
                # د) التوزيع الفوري (سيشمل الآن الأفراد والمجموعات)
                logger.info("🚀 Broadcasting to ALL (Groups + Private Users)...")
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, sent_message.message_id)
                
                os.remove(image_path)
                return

            except Exception as e:
                logger.error(f"⚠️ Art Failed: {e}", exc_info=True)
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)
        
        else:
            # ميديا
            logger.info(f"📢 Broadcasting Raw Media: {message.message_id}")
            await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    async with AsyncSessionLocal() as session:
        # يمكننا مستقبلاً التفريق بين المجموعات والأفراد في الإحصائيات
        count = await session.scalar(select(func.count()).select_from(Subscriber))
    await update.message.reply_text(f"📊 *إحصائيات قاعدة البيانات*\n👥 إجمالي المشتركين: `{count}`", parse_mode=ParseMode.MARKDOWN)

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready. Private User Tracking Enabled.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    
    # 1. أمر البداية (للأفراد) - مهم أن يكون في البداية
    application.add_handler(CommandHandler("start", start_command))
    
    # 2. متابعة المجموعات
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # 3. أوامر الإدارة
    application.add_handler(CommandHandler("stats", stats_command))
    
    # 4. معالج القناة المصدر
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()