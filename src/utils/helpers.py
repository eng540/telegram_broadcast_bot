import logging
from telegram import Bot
from telegram.constants import ParseMode
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import BotUser
from src.config import settings
from src.services.content_manager import content

logger = logging.getLogger(__name__)

async def notify_admin(bot: Bot, text: str):
    try:
        await bot.send_message(
            chat_id=settings.ADMIN_ID,
            text=f"🔔 **إشعار:**\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
    except: pass

async def ensure_user_exists(user, bot: Bot = None):
    if not user: return None
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BotUser).where(BotUser.user_id == user.id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            session.add(BotUser(user_id=user.id, first_name=user.first_name, username=user.username, is_active=True))
            await session.commit()
            logger.info(f"👤 New User: {user.first_name}")
            if bot:
                msg = content.get("admin.new_user", name=user.first_name, id=user.id)
                await notify_admin(bot, msg)
        else:
            updated = False
            if not db_user.is_active:
                db_user.is_active = True
                updated = True
            if db_user.first_name != user.first_name:
                db_user.first_name = user.first_name
                updated = True
            if updated: await session.commit()
    return user.id