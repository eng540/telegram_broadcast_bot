import logging
import re
from telegram import Update, ChatMember
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, filters
from src.config import settings
from src.database import init_db, AsyncSessionLocal
from src.models import Subscriber
from src.services.forwarder import ForwarderService
from sqlalchemy import delete

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

forwarder = ForwarderService()

# الروابط المسموح بها (قناتك)
ALLOWED_LINK = "t.me/Rwaea3" 

def is_ad(message) -> bool:
    """
    دالة الفلترة الشاملة: تمنع الروابط الخارجية + تمنع الرسائل المحولة (Forwards)
    """
    
    # --- 1. فحص إعادة التوجيه (Forwarding Check) ---
    # إذا كانت الرسالة تحتوي على مصدر توجيه (Forward Header)
    if message.forward_origin:
        # نحاول معرفة القناة الأصلية
        origin_chat = getattr(message.forward_origin, 'chat', None)
        
        # الحالة الوحيدة المسموحة: أن تكون محولة من "نفس القناة المصدر" (تذكير بمنشور قديم)
        if origin_chat and origin_chat.id == settings.MASTER_SOURCE_ID:
            pass # مسموح، أكمل الفحص
        else:
            # أي حالة أخرى (قناة أخرى، شخص، مصدر مخفي) -> نعتبرها دعم/إعلان
            logger.info("🚫 Detected Forwarded Post (Support/Cross-promo). Skipping.")
            return True # هذا إعلان (احظره)

    # --- 2. فحص الروابط النصية (Links Check) ---
    text = message.text or message.caption or ""
    
    if text:
        # البحث عن الروابط
        url_pattern = r"(https?://[^\s]+)|(t\.me/[^\s]+)|(telegram\.me/[^\s]+)"
        found_urls = re.findall(url_pattern, text)

        for url_tuple in found_urls:
            url = "".join(url_tuple).lower()
            # إذا وجد رابطاً ليس لقناتنا -> حظر
            if ALLOWED_LINK.lower() not in url:
                logger.info(f"🚫 Detected Link Ad ({url}). Skipping.")
                return True

    return False

# --- بقية الكود كما هو ---

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
                try: await context.bot.send_message(chat_id, "🕊️ وصل الزاجل!\nتم تفعيل الخدمة.")
                except: pass

    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        
        # تطبيق الفلتر المشدد (روابط + توجيه)
        if is_ad(message):
            return
            
        await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready (Anti-Ad & Anti-Forward Active).")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # إضافة أوامر الرد البسيطة
    application.add_handler(MessageHandler(filters.COMMAND, lambda u,c: u.message.reply_text("أهلاً بك في زاجل.")))
    
    application.add_handler(MessageHandler(
        filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, 
        handle_source_post
    ))
    application.run_polling()

if __name__ == "__main__":
    main()