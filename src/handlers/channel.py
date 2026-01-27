import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.fal_design import FalDesignService 
from src.services.image_gen import ImageGenerator

logger = logging.getLogger(__name__)

forwarder = ForwarderService()
fal_designer = FalDesignService()
image_gen = ImageGenerator()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: return

    # --- 1. قفل التكرار (Deduplication Lock) ---
    # نمنع معالجة نفس الرسالة مرتين خلال دقيقة
    lock_key = f"processing_lock:{message.message_id}"
    if await forwarder.redis.get(lock_key): return
    await forwarder.redis.set(lock_key, "1", ex=60)

    # --- 2. كاسر الحلقة (Loop Breaker) ---
    # إذا كانت الرسالة تحتوي على توقيع البوت، نتجاهلها فوراً (لأنها من صنع البوت)
    content_text = message.text or message.caption or ""
    if settings.CHANNEL_HANDLE in content_text:
        logger.info("🛑 Ignoring self-generated message.")
        return

    # --- 3. معالجة الحذف (/del) ---
    if message.reply_to_message and message.text and message.text.strip() == "/del":
        logger.info("🗑️ Delete command received.")
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        try:
            await message.reply_to_message.delete()
            await message.delete()
        except: pass
        return

    # --- 4. توجيه الوسائط الجاهزة (صور/فيديو) ---
    # ✅ الإصلاح: إذا كانت الرسالة صورة أو فيديو، نرسلها كما هي ولا نصممها
    if message.photo or message.video or message.document:
        logger.info("📸 Media post detected. Broadcasting as is...")
        await forwarder.broadcast_message(context.bot, message.message_id)
        return

    # --- 5. معالجة النصوص فقط (AI Design) ---
    # إذا وصلنا هنا، فالرسالة هي "نص صافي" وتحتاج تصميم
    if not message.text: return 
    
    text = message.text
    
    # نتجاهل النصوص الطويلة جداً (مقالات)
    if len(text) > 400:
        await forwarder.broadcast_message(context.bot, message.message_id)
        return

    logger.info("🎨 Text post detected. Starting AI Design...")
    
    # أ) طلب الخلفية من Fal.ai (Flux Schnell)
    bg_data = await fal_designer.generate_background_b64(text)
    
    # ب) الدمج والكتابة
    try:
        image_path = await image_gen.render(text, message.message_id, bg_data)
        
        # تجهيز الكابشن
        lines = [line for line in text.split('\n') if line.strip()]
        excerpt = lines[0][:50] + "..." if lines else ""
        caption = f"❝ {excerpt}\n\n💎 {settings.CHANNEL_HANDLE}"

        # ج) الإرسال للقناة المصدر
        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=caption
            )
        
        # د) تسجيل الرسالة وتوزيعها
        # نسجل ID الرسالة الجديدة (الصورة) في Redis لنعرف أنها من صنعنا
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        # تنظيف
        os.remove(image_path)
            
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        # في حال الفشل، ننشر النص الأصلي
        await forwarder.broadcast_message(context.bot, message.message_id)