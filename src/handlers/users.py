import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes
from src.utils.helpers import ensure_user_exists
from src.services.image_gen import ImageGenerator

logger = logging.getLogger(__name__)
image_gen = ImageGenerator()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != ChatType.PRIVATE: return

    await ensure_user_exists(user, context.bot)

    welcome_text = (
        f"أهلاً بك يا *{user.first_name}* 👋\n\n"
        "أنا **زاجل**، رفيقك الأدبي.\n"
        "✨ **ميزة خاصة:** أرسل لي أي نص الآن وسأحوله للوحة فنية!"
    )
    keyboard = [[InlineKeyboardButton("📢 القناة الرسمية", url="https://t.me/Rwaea3")]]
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_private_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if len(text) > 450 or len(text) < 5:
        await update.message.reply_text("⚠️ النص يجب أن يكون بين 5 و 450 حرفاً.")
        return

    await context.bot.send_chat_action(chat_id=user.id, action=constants.ChatAction.UPLOAD_PHOTO)
    status_msg = await update.message.reply_text("🎨 جاري الرسم...")

    try:
        image_path = await image_gen.render(text, update.message.message_id)
        with open(image_path, 'rb') as f:
            await update.message.reply_photo(
                photo=f,
                caption="✍️ **تصميم خاص لك**",
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        await status_msg.delete()
        os.remove(image_path)
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        await status_msg.edit_text("حدث خطأ فني.")