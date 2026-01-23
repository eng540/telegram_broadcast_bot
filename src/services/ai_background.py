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
            # نستخدم FLUX Schnell لأنه سريع ومجاني وممتاز للخلفيات
            self.model = "black-forest-labs/FLUX.1-schnell"
            self.client = InferenceClient(token=self.token)
        else:
            self.client = None

    async def generate(self, mood_text: str) -> str:
        """توليد خلفية فنية بناءً على النص"""
        if not self.client: return None
        
        logger.info(f"🎨 Generating background via HuggingFace...")
        
        # نطلب خلفية ضبابية قليلاً لتناسب الكتابة
        prompt = f"""
        Abstract artistic background representing: {mood_text}.
        Style: Islamic geometry patterns, Cinematic lighting, Soft focus, Blur effect, 8k resolution.
        Colors: Gold, Dark Blue, Black, Deep Red.
        NO TEXT, NO LETTERS. Just pure background texture.
        """

        try:
            def call_api():
                return self.client.text_to_image(prompt=prompt, model=self.model)

            image = await asyncio.to_thread(call_api)
            
            if image:
                # حفظ الصورة مؤقتاً
                filename = f"bg_{hash(mood_text)}.jpg"
                path = os.path.join("/app/data", filename)
                image.save(path)
                return path # نرجع مسار الملف المحلي
            
            return None
        except Exception as e:
            logger.error(f"❌ AI Background Failed: {e}")
            return None