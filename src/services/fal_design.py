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
        # ✅ نستخدم أرخص نموذج (Flux Schnell) بناءً على تحليل الفاتورة
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background(self, text: str) -> str:
        """توليد خلفية فنية فقط (بدون نص) بتكلفة شبه معدومة"""
        logger.info(f"🎨 Fal.ai (Schnell) generating background...")
        
        # نطلب خلفية فنية تناسب النص
        prompt = f"""
        Abstract artistic background representing mood: "{text[:100]}".
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
                        "num_inference_steps": 4, # Schnell سريع جداً ويكتفي بـ 4 خطوات
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