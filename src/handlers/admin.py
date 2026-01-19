from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select, func
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    
    async with AsyncSessionLocal() as session:
        users = await session.scalar(select(func.count()).select_from(BotUser).where(BotUser.is_active == True))
        groups = await session.scalar(select(func.count()).select_from(TelegramGroup).where(TelegramGroup.is_active == True))
        
    await update.message.reply_text(f"📊 **التقرير:**\n👤 الأفراد: `{users}`\n🏘️ المجموعات: `{groups}`", parse_mode=ParseMode.MARKDOWN)