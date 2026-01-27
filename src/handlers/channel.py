#--- start
import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator
from src.services.fal_design import FalDesignService # الاقتصادي (خلفيات)
from src.services.google_design import GoogleDesignService # الاحترافي (كامل)

logger = logging.getLogger(__name__)

# تهيئة جميع الخدمات
forwarder = ForwarderService()
image_gen = ImageGenerator()
fal_designer = FalDesignService()
google_designer = GoogleDesignService()

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
    # هذا يحل مشكلة تكرار النشر اللانهائي
    content_text = message.text or message.caption or ""
    if settings.CHANNEL_HANDLE in content_text:
        return

    # ---------------------------------------------------------
    # 3. أوامر التحكم اليدوي (PRO / DELETE)
    # ---------------------------------------------------------
    if message.reply_to_message and message.text:
        command = message.text.strip().lower()
        
        # أ) حذف (/del)
        if command == "/del":
            logger.info("🗑️ Delete command received.")
            await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
            try: 
                await message.reply_to_message.delete()
                await message.delete()
            except: pass
            return

        # ب) تصميم احترافي (/pro) - يستخدم Google Gemini 3
        if command == "/pro":
            original_text = message.reply_to_message.text or message.reply_to_message.caption
            if not original_text: return
            
            logger.info("💎 Manual PRO trigger received.")
            await context.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
            
            # استدعاء المحرك الذكي (جوجل)
            image_path = await google_designer.generate_pro_design(original_text, message.message_id)
            
            if image_path:
                with open(image_path, 'rb') as f:
                    sent = await context.bot.send_photo(
                        chat_id=settings.MASTER_SOURCE_ID,
                        photo=f,
                        caption=f"✨ {settings.CHANNEL_HANDLE}"
                    )
                # نوزع النسخة الاحترافية
                await forwarder.broadcast_message(context.bot, sent.message_id)
                
                # تنظيف
                try: await message.delete() # نحذف الأمر /pro
                except: pass
                os.remove(image_path)
            return

    # ---------------------------------------------------------
    # 4. معالجة الوسائط الجاهزة (صور/فيديو)
    # ---------------------------------------------------------
    # إذا نشرت صورة أو فيديو، البوت يوزعها كما هي ولا يحاول تصميمها
    # هذا يحل مشكلة "تصميم الكاباتشا" أو الصور العشوائية
    if message.photo or message.video or message.document:
        logger.info("📸 Media post detected. Broadcasting as is...")
        await forwarder.broadcast_message(context.bot, message.message_id)
        return

    # ---------------------------------------------------------
    # 5. النشر التلقائي (الاقتصادي - للنصوص فقط)
    # ---------------------------------------------------------
    text = message.text
    if not text: return

    # نتجاهل النصوص الطويلة جداً (أكثر من 400 حرف) لتجنب تشوه التصميم
    if len(text) > 400:
        await forwarder.broadcast_message(context.bot, message.message_id)
        return

    logger.info("🎨 Starting Economy Design...")
    
    # أ) خلفية رخيصة (Flux Schnell)
    bg_data = await fal_designer.generate_background_b64(text)
    
    # ب) دمج بالكود (مجاني واحترافي)
    try:
        image_path = await image_gen.render(text, message.message_id, bg_data)
        
        lines = [line for line in text.split('\n') if line.strip()]
        excerpt = lines[0][:50] + "..." if lines else ""
        caption = f"❝ {excerpt}\n\n💎 {settings.CHANNEL_HANDLE}"

        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=caption
            )
        
        # تسجيل الرسالة (مهم للحذف لاحقاً)
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        
        # توزيع
        await forwarder.broadcast_message(context.bot, sent.message_id)
        
        os.remove(image_path)
            
    except Exception as e:
        logger.error(f"Design Failed: {e}")
        # في حال الفشل، ننشر النص كما هو
        await forwarder.broadcast_message(context.bot, message.message_id)