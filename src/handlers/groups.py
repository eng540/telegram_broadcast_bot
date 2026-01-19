from telegram import Update, ChatMember
from telegram.constants import ChatType
from telegram.ext import ContextTypes
from sqlalchemy import select, update
from src.database import AsyncSessionLocal
from src.models import TelegramChannel, TelegramGroup
from src.utils.helpers import ensure_user_exists, notify_admin
from src.services.content_manager import content

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    new = result.new_chat_member
    chat = result.chat
    
    async with AsyncSessionLocal() as session:
        if new.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            owner_id = await ensure_user_exists(result.from_user, context.bot)
            
            if chat.type == ChatType.CHANNEL:
                existing = await session.scalar(select(TelegramChannel).where(TelegramChannel.chat_id == chat.id))
                if not existing:
                    session.add(TelegramChannel(chat_id=chat.id, title=chat.title, added_by_id=owner_id, is_active=True))
                    await notify_admin(context.bot, content.get("admin.new_channel", title=chat.title, by=result.from_user.first_name))
            else:
                existing = await session.scalar(select(TelegramGroup).where(TelegramGroup.chat_id == chat.id))
                if not existing:
                    session.add(TelegramGroup(chat_id=chat.id, title=chat.title, added_by_id=owner_id, is_active=True))
                    await notify_admin(context.bot, content.get("admin.new_group", title=chat.title, by=result.from_user.first_name))
                    try: await context.bot.send_message(chat.id, "🕊️ وصل الزاجل!")
                    except: pass
            await session.commit()
        
        elif new.status in [ChatMember.LEFT, ChatMember.BANNED]:
            model = TelegramChannel if chat.type == ChatType.CHANNEL else TelegramGroup
            await session.execute(update(model).where(model.chat_id == chat.id).values(is_active=False))
            await session.commit()