from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy import select, func
from src.database import AsyncSessionLocal
from src.models import BotUser, TelegramChannel, TelegramGroup
from src.config import settings
from src.services.content_manager import content

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.ADMIN_ID: return
    
    async with AsyncSessionLocal() as session:
        u = await session.scalar(select(func.count()).select_from(BotUser).where(BotUser.is_active == True))
        c = await session.scalar(select(func.count()).select_from(TelegramChannel).where(TelegramChannel.is_active == True))
        g = await session.scalar(select(func.count()).select_from(TelegramGroup).where(TelegramGroup.is_active == True))
        
    msg = content.get("admin.stats_report", users=u, channels=c, groups=g, total=u+c+g)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)