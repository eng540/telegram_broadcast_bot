import logging
import os
import asyncio
from telegram import Update, ChatMember
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, ContextTypes, MessageHandler, ChatMemberHandler, CommandHandler, filters
from sqlalchemy import select, func, update
from src.config import settings
from src.database import init_db, AsyncSessionLocal
# استيراد النماذج الثلاثة
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.services.forwarder import ForwarderService
from src.services.filters import FilterService
from src.services.image_gen import ImageGenerator

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تهيئة الخدمات
forwarder = ForwarderService()
image_gen = ImageGenerator()

# --- 🛠️ دالة ذكية لإدارة المستخدمين (Soft Logic Core) ---
async def ensure_user_exists(session, user):
    """
    تتأكد من وجود المستخدم، وتقوم بإعادة تفعيله إذا كان 'غير نشط'.
    """
    if not user: return None
    
    # البحث عن المستخدم
    result = await session.execute(select(BotUser).where(BotUser.user_id == user.id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        # تسجيل جديد
        new_user = BotUser(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username,
            is_active=True
        )
        session.add(new_user)
        # Flush للحصول على ID لاستخدامه في العلاقات فوراً
        await session.flush() 
        logger.info(f"👤 New User Registered: {user.first_name} ({user.id})")
    else:
        # تحديث البيانات + إعادة التفعيل (Soft Logic)
        updated = False
        if not db_user.is_active:
            db_user.is_active = True
            logger.info(f"♻️ User Reactivated: {user.first_name}")
            updated = True
        
        # تحديث الاسم والمعرف إذا تغيرا
        if db_user.first_name != user.first_name:
            db_user.first_name = user.first_name
            updated = True
        if db_user.username != user.username:
            db_user.username = user.username
            updated = True
            
        if updated:
            # وضعنا flush هنا لضمان تحديث الكائن في الجلسة الحالية
            await session.flush()

    return user.id

# --- 1. التعامل مع الأفراد (/start) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # نتأكد أن الأمر في الخاص فقط
    if chat.type != ChatType.PRIVATE:
        return

    async with AsyncSessionLocal() as session:
        await ensure_user_exists(session, user)
        await session.commit()

    welcome_text = (
        f"أهلاً بك يا *{user.first_name}* 🌹\n\n"
        "أنا **زاجل**، رفيقك الأدبي.\n"
        "تم تفعيل اشتراكك بنجاح، وستصلك الروائع الفنية يومياً.\n\n"
        "💎 **لأصحاب القنوات والمجموعات:**\n"
        "أضفني مشرفاً في قناتك أو مجموعتك، وسأقوم بتغذيتها بالمحتوى الراقي تلقائياً."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

# --- 2. متابعة القنوات والمجموعات (إدارة الكيانات) ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    
    new_state = result.new_chat_member
    chat = result.chat
    added_by_user = result.from_user 
    
    async with AsyncSessionLocal() as session:
        # البوت أصبح عضواً أو مشرفاً (Active)
        if new_state.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            # أولاً: نضمن تسجيل المالك
            owner_id = await ensure_user_exists(session, added_by_user)
            
            # ثانياً: معالجة القنوات
            if chat.type == ChatType.CHANNEL:
                res = await session.execute(select(TelegramChannel).where(TelegramChannel.chat_id == chat.id))
                db_channel = res.scalar_one_or_none()
                
                if not db_channel:
                    new_channel = TelegramChannel(chat_id=chat.id, title=chat.title, added_by_id=owner_id, is_active=True)
                    session.add(new_channel)
                    logger.info(f"📢 New Channel: {chat.title}")
                else:
                    if not db_channel.is_active:
                        db_channel.is_active = True # إعادة تفعيل
                        logger.info(f"♻️ Channel Reactivated: {chat.title}")
                    # تحديث العنوان و المالك
                    db_channel.title = chat.title
                    db_channel.added_by_id = owner_id

            # ثالثاً: معالجة المجموعات
            elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                res = await session.execute(select(TelegramGroup).where(TelegramGroup.chat_id == chat.id))
                db_group = res.scalar_one_or_none()
                
                if not db_group:
                    new_group = TelegramGroup(chat_id=chat.id, title=chat.title, added_by_id=owner_id, is_active=True)
                    session.add(new_group)
                    logger.info(f"🏘️ New Group: {chat.title}")
                    try: await context.bot.send_message(chat.id, "🕊️ وصل الزاجل!\nتم تفعيل الخدمة.")
                    except: pass
                else:
                    if not db_group.is_active:
                        db_group.is_active = True # إعادة تفعيل
                        logger.info(f"♻️ Group Reactivated: {chat.title}")
                    db_group.title = chat.title
                    db_group.added_by_id = owner_id
        
        # البوت طُرد أو غادر (Soft Delete)
        elif new_state.status in [ChatMember.LEFT, ChatMember.BANNED]:
            if chat.type == ChatType.CHANNEL:
                stmt = update(TelegramChannel).where(TelegramChannel.chat_id == chat.id).values(is_active=False)
                await session.execute(stmt)
                logger.info(f"💤 Channel Deactivated: {chat.title}")
            else:
                stmt = update(TelegramGroup).where(TelegramGroup.chat_id == chat.id).values(is_active=False)
                await session.execute(stmt)
                logger.info(f"💤 Group Deactivated: {chat.title}")

        await session.commit()

# --- 3. النشر الذكي (Text to Art & Broadcast) ---
async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == settings.MASTER_SOURCE_ID:
        message = update.channel_post
        if not message: return
        
        # تجاهل رسائل البوت نفسه
        if message.from_user and message.from_user.id == context.bot.id: return

        # الفلترة
        if FilterService.is_ad(message): return

        # تحليل المحتوى
        is_text_only = (message.text is not None) and (not message.photo) and (not message.video)
        text_content = message.text or ""
        
        # مسار 1: تحويل النص لصورة فنية
        # زدنا الحد لـ 3000 لدعم القصائد الطويلة جداً
        if is_text_only and 5 < len(text_content) < 3000:
            logger.info(f"🎨 Art Generation Triggered: {message.message_id}")
            try:
                # أ) التصميم
                image_path = await image_gen.render(text_content, message.message_id)
                
                # ب) الكابشن
                caption_part = text_content.split('\n')[0]
                if len(caption_part) > 100: caption_part = caption_part[:97] + "..."
                
                # ج) الإرسال للقناة المصدر
                with open(image_path, 'rb') as f:
                    sent_msg = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID, 
                        photo=f, 
                        caption=caption_part, 
                        reply_to_message_id=message.message_id
                    )
                
                # د) التوزيع الفوري (للكيانات النشطة فقط)
                logger.info("🚀 Broadcasting Generated Art...")
                await forwarder.broadcast_message(context.bot, sent_msg.message_id)
                
                # تنظيف
                os.remove(image_path)
                
            except Exception as e:
                logger.error(f"⚠️ Art Gen Failed: {e}", exc_info=True)
                # خطة بديلة: نشر النص الأصلي
                await forwarder.broadcast_message(context.bot, message.message_id)
        
        # مسار 2: نشر الميديا الجاهزة
        else:
            logger.info(f"📢 Broadcasting Raw Media: {message.message_id}")
            await forwarder.broadcast_message(context.bot, message.message_id)

# --- 4. إحصائيات دقيقة (Active Only) ---
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    
    async with AsyncSessionLocal() as session:
        # حساب النشطين فقط
        active_users = await session.scalar(select(func.count()).select_from(BotUser).where(BotUser.is_active == True))
        active_channels = await session.scalar(select(func.count()).select_from(TelegramChannel).where(TelegramChannel.is_active == True))
        active_groups = await session.scalar(select(func.count()).select_from(TelegramGroup).where(TelegramGroup.is_active == True))
        
        # حساب الإجمالي (للمقارنة)
        total_users = await session.scalar(select(func.count()).select_from(BotUser))
        
    report = (
        f"📊 **التقرير المباشر (الكيانات النشطة)**\n\n"
        f"👤 **الأفراد:** `{active_users}` (من أصل {total_users})\n"
        f"📢 **القنوات:** `{active_channels}`\n"
        f"🏘️ **المجموعات:** `{active_groups}`\n\n"
        f"🟢 **الحالة:** النظام يعمل بكفاءة Soft Logic."
    )
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

async def post_init(app: Application):
    await init_db()
    logger.info("🛡️ System Ready. Logic: Soft Delete & Auto-Recovery.")

def main():
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Chat(settings.MASTER_SOURCE_ID) & filters.UpdateType.CHANNEL_POST, handle_source_post))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()