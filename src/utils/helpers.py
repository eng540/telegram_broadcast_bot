import logging
from telegram import Bot
from telegram.constants import ParseMode
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import BotUser
from src.config import settings

logger = logging.getLogger(__name__)

async def notify_admin(bot: Bot, text: str):
    """إرسال إشعار للمدير"""
    try:
        await bot.send_message(
            chat_id=settings.ADMIN_ID,
            text=f"🔔 **إشعار:**\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.warning(f"Failed to notify admin: {e}")

async def ensure_user_exists(user, bot: Bot = None):
    """تسجيل المستخدم أو تحديث بياناته"""
    if not user: return None
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BotUser).where(BotUser.user_id == user.id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            new_user = BotUser(
                user_id=user.id,
                first_name=user.first_name,
                username=user.username,
                is_active=True
            )
            session.add(new_user)
            await session.commit()
            logger.info(f"👤 New User: {user.first_name}")
            if bot:
                await notify_admin(bot, f"👤 **مشترك جديد:** {user.first_name}\n🆔 `{user.id}`")
        else:
            changed = False
            if not db_user.is_active:
                db_user.is_active = True
                changed = True
            if db_user.first_name != user.first_name:
                db_user.first_name = user.first_name
                changed = True
            
            if changed:
                await session.commit()
    
    return user.id