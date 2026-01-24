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
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background(self, text: str) -> str:
        logger.info(f"🎨 Fal.ai (Schnell) generating background...")
        
        prompt = f"""
        Abstract artistic background representing: "{text[:100]}".
        Style: Cinematic, Islamic Art patterns, soft lighting, elegant, 8k resolution.
        Colors: Dark, Gold, Deep Blue.
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
                
                # 🔥 التغيير الجوهري: تحميل الصورة فوراً
                return await self._download_image(image_url)
            
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Failed: {e}")
            return None

    async def _download_image(self, url: str) -> str:
        """تحميل الصورة من الرابط وحفظها محلياً"""
        try:
            def download():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    # اسم ملف فريد
                    filename = f"bg_{uuid.uuid4()}.jpg"
                    path = os.path.join(output_dir, filename)
                    with open(path, 'wb') as f:
                        f.write(response.content)
                    return path
                return None

            local_path = await asyncio.to_thread(download)
            if local_path:
                logger.info(f"📥 Background downloaded to: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download background: {e}")
            return None