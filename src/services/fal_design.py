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
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux-pro/v1.1-ultra"

    async def generate_background(self, text_mood: str) -> str:
        """توليد خلفية فنية فقط (بدون نص)"""
        logger.info(f"🎨 Generating Background for mood: {text_mood[:30]}...")
        
        prompt = f"""
        A breathtaking, artistic background image.
        Theme: {text_mood}
        Style: Cinematic, Islamic Art patterns, soft lighting, elegant, 8k resolution.
        IMPORTANT: NO TEXT, NO LETTERS, NO WATERMARKS. Just pure art and background.
        Center area should be slightly darker or cleaner to allow text overlay later.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "safety_tolerance": "2",
                        "num_inference_steps": 28,
                        "guidance_scale": 3.5
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)
            
            if result and 'images' in result and len(result['images']) > 0:
                return result['images'][0]['url']
            
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Failed: {e}")
            return None