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
        
        # ✅ استخدام نموذج جوجل الأقوى للكتابة
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يرسل النص لـ Fal.ai (Google Gemini 3) للرسم والكتابة
        """
        logger.info(f"🎨 Fal.ai (Gemini 3) is working on: {text[:30]}...")
        
        # هندسة الأمر (Prompt Engineering) لضمان كتابة النص
        prompt = f"""
        Act as a professional Arabic Calligrapher and Artist.
        
        TASK: Create a stunning poster with the following Arabic text written in the center:
        "{text}"
        
        REQUIREMENTS:
        1. TEXT: The Arabic text must be written clearly, correctly, and legibly. Use elegant calligraphy.
        2. BACKGROUND: Cinematic, artistic, moody background that matches the text's emotion. (Islamic patterns, nature, or abstract).
        3. COLOR: Ensure high contrast between text and background (e.g., Gold text on Dark Blue background).
        
        Output: High quality image.
        """

        try:
            # دالة الاتصال
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3", # دقة ممتازة وتكلفة معقولة
                        "num_inference_steps": 30,
                        "guidance_scale": 3.5
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