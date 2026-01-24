import logging
import os
import asyncio
import fal_client
import requests
from src.config import settings

logger = logging.getLogger("GoogleDesignService")

class GoogleDesignService:
    def __init__(self):
        if not settings.FAL_KEY: return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        # النموذج الاحترافي الكامل (كتابة + رسم)
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_pro_design(self, text: str, message_id: int) -> str:
        """تصميم احترافي كامل (نص + صورة) باستخدام جوجل"""
        logger.info(f"💎 PRO Design requested for: {text[:30]}...")
        
        prompt = f"""
        Act as a professional Arabic Calligrapher and Digital Artist.
        TASK: Create a cinematic poster.
        
        TEXT TO WRITE (CENTER): "{text}"
        
        STYLE:
        - Font: Majestic Arabic Calligraphy (Thuluth/Diwani).
        - Color: Gold/White High Contrast.
        - Background: Artistic, moody, cinematic lighting, 8k resolution.
        - Composition: The text must be the HERO of the image.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 30, # جودة قصوى
                        "guidance_scale": 3.5
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