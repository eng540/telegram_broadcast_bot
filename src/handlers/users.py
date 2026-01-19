import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, CallbackQueryHandler
from src.utils.helpers import ensure_user_exists
from src.config import settings
from src.services.content_manager import content
from src.services.image_gen import ImageGenerator

image_gen = ImageGenerator()

# --- 1. أمر البداية (منطق فقط) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != ChatType.PRIVATE: return

    await ensure_user_exists(user, context.bot)

    # جلب النصوص من ملف yaml
    header = content.get("welcome.header", name=user.first_name)
    body = content.get("welcome.body") # bot_name يأتي تلقائياً من الإعدادات
    text = f"{header}\n\n{body}"
    
    # جلب نصوص الأزرار
    btn_group = content.get("welcome.buttons.add_group")
    btn_help = content.get("welcome.buttons.how_to_channel")
    btn_channel = content.get("welcome.buttons.channel")

    keyboard = [
        [InlineKeyboardButton(btn_group, url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton(btn_help, callback_data="how_to_channel")],
        [InlineKeyboardButton(btn_channel, url=settings.CHANNEL_LINK)]
    ]
    
    await update.message.reply_text(
        text, 
        parse_mode=ParseMode.MARKDOWN, 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- 2. معالج زر الشرح (Callback) ---
async def help_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # جلب تعليمات المساعدة وتمرير معرف البوت كمتغير
    help_text = content.get("help.channel_instructions", bot_username=context.bot.username)
    
    await query.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# --- 3. ميزة التصميم ---
async def handle_private_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if len(text) > 450:
        await update.message.reply_text(content.get("art.error_too_long"))
        return
    if len(text) < 3:
        return

    await context.bot.send_chat_action(chat_id=user.id, action=constants.ChatAction.UPLOAD_PHOTO)
    
    try:
        image_path = await image_gen.render(text, update.message.message_id)
        
        # الكابشن يأتي من الملف أيضاً
        caption_text = content.get("art.caption")
        
        with open(image_path, 'rb') as f:
            await update.message.reply_photo(
                photo=f,
                caption=caption_text,
                reply_to_message_id=update.message.message_id
            )
        os.remove(image_path)

    except Exception:
        await update.message.reply_text(content.get("art.error_generic"))