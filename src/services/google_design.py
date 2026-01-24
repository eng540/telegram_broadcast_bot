# --- START OF FILE src/services/google_design.py ---
import logging
import os
import asyncio
import fal_client
import requests
from src.config import settings

logger = logging.getLogger("GoogleDesignService")

class GoogleDesignService:
    def __init__(self):
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY is missing.")
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        # الحقيقة الثابتة: النموذج المعتمد في الكود
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    def _analyze_context(self, text: str) -> dict:
        """
        🧠 محرك تحليل السياق: يحدد الروح الفنية للنص بدلاً من الستايل الثابت.
        """
        # 1. السياق الروحاني / الديني
        if any(w in text for w in ['الله', 'رب', 'نور', 'روح', 'دعاء', 'قلب', 'إيمان']):
            return {
                "theme": "Spiritual & Divine",
                "font_style": "Majestic Thuluth or flowing Diwani",
                "palette": "Ethereal Gold, Azure Blue, Pearlescent White light",
                "atmosphere": "Mystical, volumetric sun rays, celestial glow, awe-inspiring",
                "integration": "Text formed by glowing light beams integrated into sacred architecture"
            }
        # 2. السياق الحزين / العميق
        elif any(w in text for w in ['ليل', 'حزن', 'فراق', 'ألم', 'دمع', 'وحدة', 'غياب']):
            return {
                "theme": "Melancholic & Deep Emotion",
                "font_style": "Expressive, slightly rough or textured Arabic script",
                "palette": "Muted tones, Deep Charcoal, Desaturated Blues, touch of faded crimson",
                "atmosphere": "Moody, cinematic shadow play (chiaroscuro), rain streaks, emotional",
                "integration": "Text appears weathered, etched into an ancient sorrowful surface"
            }
        # 3. سياق القوة / الفخر / المجد
        elif any(w in text for w in ['عز', 'مجد', 'سيف', 'قوة', 'نصر', 'خيل', 'فخر']):
            return {
                "theme": "Heroic & Powerful",
                "font_style": "Bold Geometric Kufic or Strong Thuluth",
                "palette": "Royal Red, Burnished Gold, Obsidian Black, Bronze",
                "atmosphere": "Epic, dramatic sunset lighting, historic grandeur, resilient",
                "integration": "Text forged from metal or carved into monumental stone"
            }
        # 4. السياق الافتراضي: فخامة عصرية
        else:
            return {
                "theme": "Modern Luxury & Elegance",
                "font_style": "Contemporary Fluid Arabic Calligraphy",
                "palette": "Champagne Gold, Cream, Dark Marble textures",
                "atmosphere": "Sophisticated studio lighting, clean, high-end editorial feel",
                "integration": "Text flowing seamlessly with abstract luxury materials like silk or marble"
            }

    async def generate_pro_design(self, text: str, message_id: int) -> str:
        """تصميم احترافي عالمي يعتمد على تحليل السياق"""
        if not settings.FAL_KEY: return None
        
        # 1. تحليل النص لاستخراج التوجيهات الفنية
        context = self._analyze_context(text)
        logger.info(f"💎 Designing with Context: {context['theme']} for text: {text[:20]}...")

        # 2. هندسة البرومبت المتطورة (World-Class Prompt Engineering)
        prompt = f"""
        Role: World-class Arabic Calligrapher and Conceptual Digital Artist.
        Project: Create a masterpiece cinematic poster symbolizing "{context['theme']}".
        
        CRITICAL TASK: Accurately and artistically write the Arabic text below as the central hero element.
        TEXT TO WRITE: "{text}"
        
        ART DIRECTION & STYLE:
        1. Typography: {context['font_style']}.
        2. Integration: {context['integration']}. The text must feel part of the world, not just placed on top.
        3. Color Palette: {context['palette']}.
        4. Atmosphere & Mood: {context['atmosphere']}.
        5. Composition: Cinematic, balanced, focusing power on the text. 8k resolution, highly detailed textures.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        # ✅ تحسين الكفاءة: زيادة الخطوات لنتائج أدق مع النماذج المعقدة
                        "num_inference_steps": 55, 
                        # ✅ تحسين الالتزام: زيادة مقياس التوجيه لضمان كتابة النص بدقة
                        "guidance_scale": 5.5 
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                return await self._download_image(image_url, message_id)

            return None
        except Exception as e:
            logger.error(f"❌ PRO Design Failed: {e}")
            return None

    async def _download_image(self, url: str, message_id: int) -> str:
        try:
            def download():
                response = requests.get(url, timeout=60)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"pro_{message_id}.png")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                return None
            return await asyncio.to_thread(download)
        except: return None