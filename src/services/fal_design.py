import logging
import os
import asyncio
import fal_client
import requests
import base64
import random
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY: return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    def _detect_mood(self, text: str) -> dict:
        """تحليل بسيط للنص لتحديد جو الصورة والألوان"""
        text = text.lower()
        
        # 1. نمط الصباح والأمل
        if any(w in text for w in ['صبح', 'شمس', 'نور', 'ضياء', 'أمل', 'سعادة', 'فرح', 'بسمة', 'زهر', 'ورد', 'جمال']):
            return {
                "desc": "A beautiful sunrise landscape, soft morning light, flowers, blurred background",
                "colors": "Pastel, White, Light Blue, Gold"
            }
        
        # 2. نمط الليل والحزن
        elif any(w in text for w in ['ليل', 'ظلام', 'سهر', 'قمر', 'حزن', 'ألم', 'فراق', 'دمع', 'هم', 'وجع', 'موت']):
            return {
                "desc": "A dark cinematic night sky, stars, moon, moody atmosphere, mysterious fog",
                "colors": "Dark Blue, Black, Silver, Deep Purple"
            }
            
        # 3. نمط الطبيعة
        elif any(w in text for w in ['بحر', 'مطر', 'غيم', 'سماء', 'شجر', 'طبيعة', 'نهر', 'جبل', 'أرض']):
            return {
                "desc": "Majestic nature landscape, mountains and clouds, cinematic lighting, hyper-realistic",
                "colors": "Green, Earthy Browns, Sky Blue, Teal"
            }
        
        # 4. نمط الحكمة (الافتراضي)
        else:
            options = [
                {"d": "Abstract Islamic geometric patterns, elegant texture, soft depth of field", "c": "Gold, Turquoise, Beige"},
                {"d": "Vintage paper texture, old library atmosphere, cinematic lighting", "c": "Sepia, Brown, Black"},
                {"d": "Abstract fluid art, marble texture, clean and modern", "c": "White, Gold, Grey"}
            ]
            choice = random.choice(options)
            return {"desc": choice["d"], "colors": choice["c"]}

    async def generate_background_b64(self, text: str) -> str:
        """توليد خلفية نظيفة تماماً (بدون إرسال النص العربي للموديل)"""
        
        # 1. تحديد المزاج
        mood = self._detect_mood(text)
        logger.info(f"🎨 Detected Mood: {mood['desc']}")
        
        # 2. هندسة الأمر (Prompt) - خالي من النص العربي تماماً
        # نطلب منه خلفية ضبابية (Blurry/Bokeh) لتكون مثالية للكتابة فوقها
        prompt = f"""
        High-quality background wallpaper.
        Subject: {mood['desc']}.
        Color Palette: {mood['colors']}.
        
        Style: 8k resolution, Soft Focus, Bokeh Effect, Minimalist, Cinematic Lighting.
        
        CRITICAL RULES:
        - PURE BACKGROUND ONLY.
        - NO TEXT.
        - NO LETTERS.
        - NO WATERMARKS.
        - NO CALLIGRAPHY.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 4,
                        "enable_safety_checker": True
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)
            
            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                return await self._url_to_base64(image_url)
            
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Failed: {e}")
            return None

    async def _url_to_base64(self, url: str) -> str:
        try:
            def convert():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    b64_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:image/jpeg;base64,{b64_data}"
                return None

            return await asyncio.to_thread(convert)
        except Exception as e:
            logger.error(f"Base64 Conversion Failed: {e}")
            return None