import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings
from src.services.forwarder import ForwarderService
from src.services.image_gen import ImageGenerator

# 🔧 استيراد آمن لـ FalDesignService
try:
    from src.services.fal_design import FalDesignService
    FAL_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ FalDesignService imported successfully")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Cannot import FalDesignService: {e}")
    
    # إنشاء Fake service كبديل
    class FakeFalDesignService:
        def __init__(self):
            logger.warning("⚠️  Using FAKE FalDesignService - AI backgrounds disabled")
        
        async def generate_background(self, text: str) -> str:
            logger.info(f"🎨 FAKE: Would generate for: {text[:50]}...")
            return None
    
    FalDesignService = FakeFalDesignService
    FAL_AVAILABLE = False

forwarder = ForwarderService()
image_gen = ImageGenerator()
fal_designer = FalDesignService()

async def handle_source_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.edited_channel_post
    if not message or message.chat.id != settings.MASTER_SOURCE_ID: 
        return

    # قفل التكرار
    lock_key = f"processing_lock:{message.message_id}"
    if await forwarder.redis.get(lock_key): 
        return
    await forwarder.redis.set(lock_key, "1", ex=60)

    # معالجة الحذف
    if message.reply_to_message and message.text == "/del":
        await forwarder.delete_broadcast(context.bot, message.reply_to_message.message_id)
        try:
            await message.reply_to_message.delete()
            await message.delete()
        except: 
            pass
        return

    text = message.text or message.caption or ""
    if not text or settings.CHANNEL_HANDLE in text: 
        return

    logger.info(f"🎨 Starting Design for message_id: {message.message_id}")
    logger.info(f"📝 Text length: {len(text)} chars")

    # 🔧 1. توليد خلفية مع تسجيل تفصيلي
    bg_url = None
    
    # التحقق من توفر AI
    if FAL_AVAILABLE:
        logger.info("🤖 AI Service is AVAILABLE")
        
        # التحقق من وجود FAL_KEY
        if hasattr(settings, 'FAL_KEY') and settings.FAL_KEY:
            logger.info(f"🔑 FAL_KEY exists: {settings.FAL_KEY[:8]}...")
            
            try:
                logger.info(f"🚀 Calling Fal.ai for: '{text[:50]}...'")
                bg_url = await fal_designer.generate_background(text)
                
                if bg_url and bg_url.startswith('http'):
                    logger.info(f"✅ AI Background SUCCESS: {bg_url[:60]}...")
                elif bg_url is None:
                    logger.warning("⚠️  AI returned None")
                elif bg_url == "":
                    logger.warning("⚠️  AI returned empty string")
                else:
                    logger.warning(f"⚠️  AI returned unexpected: {type(bg_url)}")
                    
            except Exception as e:
                logger.error(f"❌ Fal.ai EXCEPTION: {e}")
                bg_url = None
        else:
            logger.error("❌ FAL_KEY is missing in settings!")
            bg_url = None
    else:
        logger.warning("🤖 AI Service is NOT AVAILABLE (using fallbacks)")
        bg_url = None

    # 📊 تسجيل حالة الخلفية النهائية
    logger.info(f"📦 FINAL bg_url to pass: {bg_url}")
    
    if bg_url is None:
        logger.info("🔄 Will use FALLBACK backgrounds in ImageGenerator")
    else:
        logger.info(f"🎯 Will use AI background in ImageGenerator")

    # 🎨 2. توليد الصورة (ImageGenerator سيتعامل مع الباقي)
    try:
        logger.info(f"🖼️  Calling ImageGenerator.render()...")
        image_path = await image_gen.render(text, message.message_id, bg_url)
        logger.info(f"✅ Image generated at: {image_path}")

        # تجهيز الكابشن
        lines = [line for line in text.split('\n') if line.strip()]
        excerpt = lines[0][:50] + "..." if lines else ""
        caption = f"❝ {excerpt}\n\n💎 {settings.CHANNEL_HANDLE}"

        # إرسال الصورة
        with open(image_path, 'rb') as f:
            sent = await context.bot.send_photo(
                chat_id=settings.MASTER_SOURCE_ID,
                photo=f,
                caption=caption
            )

        # تخزين ونشر
        await forwarder.redis.set(f"bot_gen:{sent.message_id}", "1", ex=86400)
        await forwarder.broadcast_message(context.bot, sent.message_id)

        # تنظيف الملف المؤقت
        os.remove(image_path)
        logger.info("🧹 Temporary image file cleaned")

    except Exception as e:
        logger.error(f"❌ Design Failed: {e}", exc_info=True)
        # Fallback: نشر النص الأصلي
        await forwarder.broadcast_message(context.bot, message.message_id)