import logging
import os
import asyncio
import fal_client
import requests
import uuid
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
        
        # 1. نمط الصباح والأمل والتفاؤل
        if any(w in text for w in ['صبح', 'شمس', 'نور', 'ضياء', 'أمل', 'سعادة', 'فرح', 'بسمة', 'زهر', 'ورد', 'جمال']):
            return {
                "style": "Oil Painting, Soft Morning Light, Vibrant",
                "colors": "Pastel, White, Light Blue, Soft Pink, Gold",
                "atmosphere": "Bright, Airy, Hopeful, Dreamy"
            }
        
        # 2. نمط الليل والحزن والفراق (النمط الحالي)
        elif any(w in text for w in ['ليل', 'ظلام', 'سهر', 'قمر', 'حزن', 'ألم', 'فراق', 'دمع', 'هم', 'وجع', 'موت']):
            return {
                "style": "Cinematic, Dark Fantasy, Moody",
                "colors": "Dark Blue, Black, Silver, Deep Purple",
                "atmosphere": "Mysterious, Melancholic, Foggy, Night time"
            }
            
        # 3. نمط الطبيعة والتأمل
        elif any(w in text for w in ['بحر', 'مطر', 'غيم', 'سماء', 'شجر', 'طبيعة', 'نهر', 'جبل', 'أرض']):
            return {
                "style": "National Geographic Photography, Hyper-realistic",
                "colors": "Green, Earthy Browns, Sky Blue, Teal",
                "atmosphere": "Nature, Calm, Fresh, Organic"
            }
            
        # 4. نمط الحكمة والتاريخ (إسلامي/تجريدي) - الافتراضي
        else:
            # نختار عشوائياً بين عدة أنماط لكسر الملل
            styles = [
                {"s": "Islamic Geometric Art", "c": "Gold, Turquoise, Beige", "a": "Elegant, Structured"},
                {"s": "Abstract Fluid Art", "c": "Beige, Gold, Marble White", "a": "Modern, Clean"},
                {"s": "Vintage Paper & Ink", "c": "Sepia, Brown, Black", "a": "Historical, Classic"}
            ]
            choice = random.choice(styles)
            return {
                "style": choice["s"],
                "colors": choice["c"],
                "atmosphere": choice["a"]
            }

    async def generate_background_b64(self, text: str) -> str:
        """توليد خلفية متغيرة حسب المعنى"""
        
        # 1. تحديد المزاج
        mood = self._detect_mood(text)
        logger.info(f"🎨 Detected Mood: {mood['atmosphere']}")
        
        # 2. هندسة الأمر الديناميكي (Dynamic Prompt)
        prompt = f"""
        High-quality artistic background.
        Subject: Abstract representation of: "{text[:50]}".
        
        VISUAL STYLE: {mood['style']}.
        COLOR PALETTE: {mood['colors']}.
        ATMOSPHERE: {mood['atmosphere']}.
        
        COMPOSITION: Minimalist center (negative space) for text overlay.
        CRITICAL: NO TEXT, NO LETTERS, NO WATERMARKS. Just pure art.
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