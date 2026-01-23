import logging
import os
import asyncio
import fal_client
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY: return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        # نستخدم Schnell (الاقتصادي)
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background(self, text: str) -> str:
        logger.info(f"🎨 Fal.ai (Schnell) generating background...")
        
        # التعديل هنا: نطلب تكويناً يسمح بالكتابة (Minimalist / Negative Space)
        prompt = f"""
        A cinematic, moody background art representing: "{text[:100]}".
        Composition: Minimalist center, heavy details on edges only.
        Style: Dark fantasy, Islamic geometric atmosphere, soft volumetric lighting, 8k resolution.
        Colors: Deep Gold, Midnight Blue, Charcoal, Dark Red.
        IMPORTANT: The center of the image must be dark and empty to allow text overlay. NO TEXT IN IMAGE.
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
                return result['images'][0]['url']
            
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Failed: {e}")
            return None