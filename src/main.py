import logging
from telegram import Update, BotCommand
from telegram.ext import Application, ChatMemberHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from src.config import settings
from src.database import init_db

# استيراد المعالجات من ملفاتها المستقلة
from src.handlers.users import start_command, handle_private_design, help_channel_callback
from src.handlers.groups import track_chats
from src.handlers.channel import handle_source_post
from src.handlers.admin import stats_command

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def post_init(app: Application):
    """تهيئة النظام عند البدء"""
    await init_db()

    # إعداد قائمة الأوامر الجانبية
    await app.bot.set_my_commands([
        BotCommand("start", "تفعيل البوت / القائمة الرئيسية"),
        BotCommand("help", "المساعدة"),
        BotCommand("stats", "الإحصائيات (للمدير)")
    ])

    logger.info("🛡️ System Ready. All Modules Loaded Successfully.")

def main():
    """نقطة التشغيل المركزية"""
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()

    # 1. المعالجات العامة (General Handlers)
    application.add_handler(CommandHandler("start", start_command))

    # 2. معالج الأزرار التفاعلية (Callback Query) - هام لزر المساعدة الجديد
    application.add_handler(CallbackQueryHandler(help_channel_callback, pattern="how_to_channel"))

    # 3. ميزة "صمم لي" (في الخاص فقط)
    # الفلتر: خاص + نص + ليس أمراً
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_private_design))

    # 4. معالج المجموعات (تتبع الدخول والخروج)
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))

    # 5. معالج المدير
    application.add_handler(CommandHandler("stats", stats_command))

    # 6. القناة المصدر (النشر والتوزيع)
    # 🔄 التحديث: دعم المنشورات العادية والمعدلة
    application.add_handler(MessageHandler(
        filters.Chat(settings.MASTER_SOURCE_ID) & 
        (filters.UpdateType.CHANNEL_POST | filters.UpdateType.EDITED_CHANNEL_POST),
        handle_source_post
    ))

    # بدء التشغيل
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()