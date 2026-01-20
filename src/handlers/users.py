import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, CallbackQueryHandler
from src.utils.helpers import ensure_user_exists
from src.config import settings
from src.services.content_manager import content
from src.services.image_gen import ImageGenerator

# إعداد السجل الخاص بهذا الملف
logger = logging.getLogger(__name__)
image_gen = ImageGenerator()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != ChatType.PRIVATE: return

    await ensure_user_exists(user, context.bot)

    header = content.get("welcome.header", name=user.first_name)
    body = content.get("welcome.body")
    text = f"{header}\n\n{body}"
    
    keyboard = [
        [InlineKeyboardButton(content.get("welcome.buttons.add_group"), url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton(content.get("welcome.buttons.how_to_channel"), callback_data="how_to_channel")],
        [InlineKeyboardButton(content.get("welcome.buttons.channel"), url=settings.CHANNEL_LINK)]
    ]
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    help_text = content.get("help.channel_instructions", bot_username=context.bot.username)
    await query.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def handle_private_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if len(text) > 450:
        await update.message.reply_text(content.get("art.error_too_long"))
        return
    if len(text) < 3:
        return

    # إشعار المستخدم بأننا نعمل
    await context.bot.send_chat_action(chat_id=user.id, action=constants.ChatAction.UPLOAD_PHOTO)
    status_msg = await update.message.reply_text(content.get("art.processing"))

    try:
        # محاولة التصميم
        logger.info(f"🎨 Starting private design for user {user.id}...")
        image_path = await image_gen.render(text, update.message.message_id)
        
        caption_text = content.get("art.caption", excerpt="إهداء خاص")
        
        with open(image_path, 'rb') as f:
            await update.message.reply_photo(
                photo=f,
                caption=caption_text,
                reply_to_message_id=update.message.message_id
            )
        
        await status_msg.delete()
        os.remove(image_path)
        logger.info(f"✅ Design success for user {user.id}")

    except Exception as e:
        # طباعة الخطأ كاملاً في السجل لنعرف السبب
        logger.error(f"❌ Private Design Failed for user {user.id}: {e}", exc_info=True)
        
        # رسالة للمستخدم
        await status_msg.edit_text("عذراً، حدث خطأ فني أثناء الرسم. حاول مرة أخرى لاحقاً.")