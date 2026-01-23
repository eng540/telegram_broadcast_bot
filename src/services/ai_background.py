import logging
import os
import asyncio
from huggingface_hub import InferenceClient
from src.config import settings

logger = logging.getLogger("AIBackground")

class AIBackgroundService:
    def __init__(self):
        self.token = settings.HUGGINGFACE_TOKEN
        if self.token:
            # نستخدم FLUX Schnell: أسرع وأقوى نموذج مجاني حالياً
            self.model = "black-forest-labs/FLUX.1-schnell"
            self.client = InferenceClient(token=self.token)
        else:
            self.client = None
            logger.warning("⚠️ HUGGINGFACE_TOKEN missing! AI will not work.")

    async def generate(self, mood_text: str) -> str:
        """
        توليد خلفية فنية باستخدام الذكاء الاصطناعي
        """
        if not self.client: return None
        
        logger.info(f"🎨 AI Generating Background for: {mood_text[:20]}...")
        
        # هندسة الأمر (Prompt) لضمان خلفية فنية بدون نصوص مشوهة
        prompt = f"""
        Abstract artistic background representing the mood: "{mood_text}".
        Style: Cinematic, Islamic geometry patterns, Soft focus, Elegant, 8k resolution, Dark moody atmosphere.
        Colors: Gold, Deep Blue, Black.
        IMPORTANT: NO TEXT, NO LETTERS, JUST BACKGROUND TEXTURE.
        """

        try:
            # دالة الاتصال (Sync to Async)
            def call_api():
                return self.client.text_to_image(
                    prompt=prompt, 
                    model=self.model,
                    width=1024,
                    height=1024
                )

            image = await asyncio.to_thread(call_api)
            
            if image:
                # حفظ الصورة محلياً
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                # اسم ملف عشوائي لتجنب التضارب
                import uuid
                filename = f"bg_{uuid.uuid4()}.jpg"
                path = os.path.join(output_dir, filename)
                
                image.save(path)
                logger.info(f"✅ AI Background Saved: {path}")
                return path # نرجع مسار الملف
            
            return None

        except Exception as e:
            logger.error(f"❌ AI Generation Failed: {e}")
            return None