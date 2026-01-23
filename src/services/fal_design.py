import logging
import os
import asyncio
import fal_client
import requests
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY:
            logger.critical("❌ FAL_KEY is missing!")
            return
        
        # إعداد المفتاح
        os.environ["FAL_KEY"] = settings.FAL_KEY
        
        # ✅ استخدام نموذج Gemini 3 Pro (الأفضل في الكتابة)
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يرسل النص لـ Fal.ai ليقوم برسمه وكتابته (إعدادات اقتصادية)
        """
        logger.info(f"🎨 Fal.ai (Gemini) is working on: {text[:30]}...")
        
        # هندسة الأمر (Prompt Engineering)
        # نطلب منه بوضوح كتابة النص العربي
        prompt = f"""
        Create a high-quality artistic poster.
        
        1. THEME: An artistic background reflecting the mood: "{text}".
           (Style: Cinematic, Islamic Art, Soft lighting, Elegant).
        
        2. TEXT TASK (MANDATORY):
           Write the following Arabic text clearly in the center:
           "{text}"
           
           - Font: Traditional Arabic Calligraphy (Thuluth or Naskh).
           - Color: Gold or White (High contrast against background).
           - The text must be 100% legible and correct.
        """

        try:
            # دالة الاتصال
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        # ✅ ضبط الدقة لتوفير الموارد (ليس 2K ولا 4K)
                        # portrait_4_3 تعطي دقة ممتازة للجوال وتوفر في السعر
                        "image_size": "portrait_4_3", 
                    },
                    with_logs=True
                )

            # التنفيذ في الخلفية
            result = await asyncio.to_thread(run_fal)
            
            # استخراج الصورة
            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                logger.info(f"✅ Fal.ai Image Generated: {image_url}")
                
                # تحميل الصورة
                return await self._download_image(image_url, message_id)
            
            logger.warning("⚠️ Fal.ai returned no images.")
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Generation Failed: {e}")
            return None

    async def _download_image(self, url: str, message_id: int) -> str:
        try:
            def download():
                response = requests.get(url, timeout=60)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"design_{message_id}.png")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                return None

            return await asyncio.to_thread(download)
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None