import logging
import os
import asyncio
import fal_client
import requests
import base64 # المكتبة الضرورية
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY: return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background_b64(self, text: str) -> str:
        """توليد خلفية وإعادتها كنص مشفر Base64"""
        logger.info(f"🎨 Fal.ai generating background...")
        
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
                # 🔥 التحويل إلى Base64 فوراً
                return await self._url_to_base64(image_url)
            
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Failed: {e}")
            return None

    async def _url_to_base64(self, url: str) -> str:
        """تحميل الصورة وتحويلها لنص"""
        try:
            def convert():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # التشفير
                    b64_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:image/jpeg;base64,{b64_data}"
                return None

            return await asyncio.to_thread(convert)
        except Exception as e:
            logger.error(f"Base64 Conversion Failed: {e}")
            return None