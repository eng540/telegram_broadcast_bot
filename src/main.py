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
                # محاولة إرسال رسالة ترحيب (قد تفشل في القنوات وتنجح في المجموعات/الخاص)
                try: await context.bot.send_message(chat_id, "🕊️ وصل الزاجل!\nتم تفعيل الخدمة.")
                except: pass
    elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Subscriber).where(Subscriber.chat_id == chat_id))
            await session.commit()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    المنطق المحصن ضد التكرار:
    المسار 1: نص -> توليد صورة -> إرسال للقناة -> توقف.
    المسار 2: ميديا (صورة/فيديو) -> توزيع للمشتركين.
    """
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message: return
        
        # 1. الفلترة الأمنية
        if FilterService.is_ad(message):
            return
            
        # تحديد نوع الرسالة بدقة
        is_text_pure = (message.text is not None) and (not message.photo) and (not message.video) and (not message.document)
        text_content = message.text or ""
        
        # --- المسار الأول: معالجة النصوص (صناعة المحتوى) ---
        if is_text_pure and 5 < len(text_content) < 450:
            logger.info(f"🎨 Converting Text to Art: {message.message_id}")
            try:
                # 1. التصميم
                image_path = await image_gen.render(text_content, message.message_id)
                
                # 2. تجهيز الكابشن
                caption_part = text_content.split('\n')[0]
                if len(caption_part) > 100: caption_part = caption_part[:97] + "..."
                
                # 3. النشر في القناة (ليراها الجمهور وتعود لنا كحدث جديد)
                with open(image_path, 'rb') as f:
                    await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID,
                        photo=f,
                        caption=caption_part,
                        reply_to_message_id=message.message_id 
                    )
                
                # 4. التنظيف والتوقف
                os.remove(image_path)
                logger.info("✅ Art posted to channel. Waiting for Telegram loop-back to broadcast.")
                
                # هام جداً: التوقف هنا يمنع إرسال النص للمشتركين
                # المشتركون سيحصلون فقط على الصورة عندما تعود في المسار الثاني
                return 

            except Exception as e:
                logger.error(f"⚠️ Art Gen Failed: {e}")
                # في حال فشل التصميم فقط، نرسل النص كبديل
                await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)
        
        # --- المسار الثاني: التعامل مع الميديا (النشر) ---
        else:
            # هذا الكود سيعمل في حالتين:
            # 1. عندما تصل الصورة التي صممناها للتو (لأنها ليست نصاً، هي photo).
            # 2. عندما ينشر المشرف فيديو أو صورة جاهزة.
            
            logger.info(f"📢 Broadcasting Media: {message.message_id}")
            await forwarder.broadcast_message(context.bot, settings.MASTER_SOURCE_ID, message.message_id)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Subscriber))
    await update.message.reply_text(f"📊 *إحصائيات الزاجل*\n👥 المشتركون: `{count}`", parse_mode="Markdown")

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready. Loop Protection Active.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()