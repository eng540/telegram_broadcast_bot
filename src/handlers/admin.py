#--- START OF FILE telegram_broadcast_bot-main/src/handlers/admin.py ---

import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select, func
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings
from src.services.content_manager import content
from src.services.backup_service import BackupService

# تهيئة خدمة النسخ الاحتياطي
backup_service = BackupService()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات النظام"""
    if update.effective_user.id != settings.ADMIN_ID: return
    
    async with AsyncSessionLocal() as session:
        u = await session.scalar(select(func.count()).select_from(BotUser).where(BotUser.is_active == True))
        c = await session.scalar(select(func.count()).select_from(TelegramChannel).where(TelegramChannel.is_active == True))
        g = await session.scalar(select(func.count()).select_from(TelegramGroup).where(TelegramGroup.is_active == True))
        
    msg = content.get("admin.stats_report", users=u, channels=c, groups=g, total=u+c+g)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء نسخة احتياطية وإرسالها للمدير"""
    if update.effective_user.id != settings.ADMIN_ID: return
    
    # إشعار لحظي
    status_msg = await update.message.reply_text("📦 جاري تجميع البيانات وضغط النسخة الاحتياطية...")
    
    try:
        # 1. إنشاء الملف
        file_path = await backup_service.create_backup()
        filename = os.path.basename(file_path)
        
        # 2. إرسال الملف
        with open(file_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption=f"🔐 **نسخة احتياطية للنظام**\n📅 التاريخ: `{filename}`\n\nاحتفظ بهذا الملف في مكان آمن.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # 3. تنظيف
        await status_msg.delete()
        os.remove(file_path)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء النسخ: {e}")

async def restore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استعادة البيانات من ملف JSON مرسل"""
    user = update.effective_user
    if user.id != settings.ADMIN_ID: return
    
    doc = update.message.document
    caption = update.message.caption or ""
    
    # التحقق من الشروط: ملف JSON + كلمة سر في الكابشن
    if not doc.file_name.endswith('.json'):
        return # تجاهل الملفات غير الصحيحة
        
    if "restore" not in caption.lower():
        await update.message.reply_text("⚠️ لاستعادة النسخة، أعد إرسال الملف واكتب كلمة `restore` في الوصف (Caption).")
        return

    status_msg = await update.message.reply_text("♻️ جاري تحليل الملف واستعادة البيانات... الرجاء الانتظار.")
    
    download_path = f"/app/data/restore_{doc.file_name}"
    
    try:
        # 1. تحميل الملف من تيليجرام
        new_file = await doc.get_file()
        await new_file.download_to_drive(download_path)
        
        # 2. تنفيذ الاستعادة
        report = await backup_service.restore_backup(download_path)
        
        # 3. إرسال التقرير
        await status_msg.edit_text(report)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ فشلت عملية الاستعادة: {e}")
        
    finally:
        # تنظيف الملف المؤقت
        if os.path.exists(download_path):
            os.remove(download_path)