#--- START OF FILE telegram_broadcast_bot-main/src/main.py ---

import logging
import os
from telegram import Update, BotCommand
from telegram.ext import Application, ChatMemberHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from src.config import settings
from src.database import init_db

# استيراد المعالجات
from src.handlers.users import start_command, handle_private_design, help_channel_callback
from src.handlers.groups import track_chats
from src.handlers.channel import handle_source_post
from src.handlers.admin import stats_command, backup_command, restore_handler
# استيراد خدمة النسخ لاستخدامها في الجدولة
from src.services.backup_service import BackupService

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- وظيفة النسخ الاحتياطي الآلي ---
async def scheduled_backup(context):
    """إرسال نسخة احتياطية للمدير تلقائياً"""
    logger.info("📦 Starting automated backup...")
    backup_service = BackupService()
    try:
        # 1. إنشاء النسخة
        file_path = await backup_service.create_backup()
        filename = os.path.basename(file_path)
        
        # 2. إرسالها للمدير
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=settings.ADMIN_ID,
                document=f,
                filename=filename,
                caption=f"🛡️ **نسخة احتياطية آلية**\n⏰ {filename}"
            )
        
        # 3. تنظيف
        os.remove(file_path)
        logger.info("✅ Automated backup sent successfully.")
        
    except Exception as e:
        logger.error(f"❌ Automated backup failed: {e}")

async def post_init(app: Application):
    """تهيئة النظام عند البدء"""
    await init_db()

    await app.bot.set_my_commands([
        BotCommand("start", "تفعيل البوت / القائمة الرئيسية"),
        BotCommand("help", "المساعدة"),
        BotCommand("stats", "الإحصائيات (للمدير)"),
        BotCommand("backup", "نسخة احتياطية (للمدير)")
    ])

    logger.info("🛡️ System Ready. All Modules Loaded Successfully.")

def main():
    """نقطة التشغيل المركزية"""
    application = Application.builder().token(settings.BOT_TOKEN).post_init(post_init).build()

    # 1. المعالجات العامة
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(help_channel_callback, pattern="how_to_channel"))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_private_design))
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))

    # 2. معالجات المدير
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(MessageHandler(
        filters.Document.MimeType("application/json") & filters.User(settings.ADMIN_ID),
        restore_handler
    ))

    # 3. القناة المصدر
    application.add_handler(MessageHandler(
        filters.Chat(settings.MASTER_SOURCE_ID) & 
        (filters.UpdateType.CHANNEL_POST | filters.UpdateType.EDITED_CHANNEL_POST),
        handle_source_post
    ))

    # ✅ تفعيل النسخ الاحتياطي الآلي (كل 6 ساعات = 21600 ثانية)
    if application.job_queue:
        # أول نسخة بعد 5 دقائق من التشغيل، ثم كل 6 ساعات
        application.job_queue.run_repeating(scheduled_backup, interval=21600, first=300)
        logger.info("⏰ Auto-Backup Job Started (Every 6 hours).")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()