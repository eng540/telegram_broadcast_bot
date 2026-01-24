import logging
import os
import asyncio
import fal_client
import requests
import uuid
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY: return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        # نستخدم Schnell (الاقتصادي)
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background(self, text: str) -> str:
        """توليد خلفية وتحميلها محلياً"""
        logger.info(f"🎨 Fal.ai (Schnell) generating background...")
        
        prompt = f"""
        Abstract artistic background representing: "{text[:100]}".
        Style: Cinematic, Islamic Art patterns, soft lighting, elegant, 8k resolution.
        Colors: Dark, Gold, Deep Blue, Charcoal.
        IMPORTANT: NO TEXT, NO LETTERS. Just pure background art.
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
                logger.info(f"✅ Image Generated: {image_url}")
                
                # 🔥 الخطوة الحاسمة: تحميل الصورة للسيرفر
                return await self._download_image(image_url)
            
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Failed: {e}")
            return None

    async def _download_image(self, url: str) -> str:
        """تحميل الصورة من الرابط وحفظها في ملف"""
        try:
            def download():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    # اسم ملف فريد
                    filename = f"bg_{uuid.uuid4()}.jpg"
                    output_path = os.path.join(output_dir, filename)
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                return None

            return await asyncio.to_thread(download)
        except Exception as e:
            logger.error(f"Failed to download background: {e}")
            return None