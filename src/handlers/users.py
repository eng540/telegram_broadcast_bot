import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes
from src.utils.helpers import ensure_user_exists
from src.config import settings
from src.services.content_manager import content
from src.services.image_gen import ImageGenerator

image_gen = ImageGenerator()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != ChatType.PRIVATE: return

    await ensure_user_exists(user, context.bot)

    header = content.get("welcome.header", name=user.first_name)
    body = content.get("welcome.body")
    text = f"{header}\n\n{body}"
    
    keyboard = [
        [InlineKeyboardButton(content.get("welcome.buttons.channel"), url=settings.CHANNEL_LINK)],
        [InlineKeyboardButton(content.get("welcome.buttons.add_group"), url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ]
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_private_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if len(text) > 450:
        await update.message.reply_text(content.get("art.error_too_long"))
        return
    
    await context.bot.send_chat_action(chat_id=user.id, action=constants.ChatAction.UPLOAD_PHOTO)
    status = await update.message.reply_text(content.get("art.processing"))

    try:
        path = await image_gen.render(text, update.message.message_id)
        with open(path, 'rb') as f:
            await update.message.reply_photo(photo=f, caption=content.get("art.success_caption"), parse_mode=ParseMode.MARKDOWN)
        await status.delete()
        os.remove(path)
    except Exception:
        await status.edit_text(content.get("art.error_generic"))