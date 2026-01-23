import logging
import os
import asyncio
import fal_client
from src.config import settings

logger = logging.getLogger("FalAIService")

class FalDesignService:
    def __init__(self):
        # 🔍 التحقق من FAL_KEY أولاً
        if not hasattr(settings, 'FAL_KEY') or not settings.FAL_KEY:
            logger.error("❌ FAL_KEY is MISSING in settings!")
            self.model_endpoint = None
            return
        
        logger.info(f"🔑 FAL_KEY found: {settings.FAL_KEY[:8]}...")
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"
        logger.info(f"✅ FalDesignService initialized with endpoint: {self.model_endpoint}")

    async def generate_background(self, text: str) -> str:
        """توليد خلفية فنية بالذكاء الاصطناعي"""
        
        # 🔍 التحقق من التهيئة
        if not self.model_endpoint:
            logger.error("❌ Service NOT INITIALIZED - FAL_KEY missing")
            return None
        
        logger.info(f"🚀 Generating AI background for text: '{text[:50]}...'")
        
        # Prompt محسن
        prompt = f"""Beautiful abstract background for Arabic text: "{text[:80]}". 
        Style: Cinematic, elegant, soft lighting, artistic.
        Colors: Dark blue, gold accents, deep tones.
        NO TEXT, NO LETTERS, NO WORDS. Pure background only."""
        
        try:
            logger.info(f"📤 Sending to Fal.ai: {prompt[:60]}...")
            
            def run_fal():
                result = fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 4,
                        "enable_safety_checker": True
                    }
                )
                logger.info(f"📥 Fal.ai response received")
                return result

            result = await asyncio.to_thread(run_fal)
            
            # 🔍 تحليل النتيجة
            if isinstance(result, dict):
                if 'images' in result and result['images']:
                    url = result['images'][0]['url']
                    logger.info(f"✅ AI Background SUCCESS: {url[:60]}...")
                    return url
                else:
                    logger.error(f"❌ No images in result. Keys: {list(result.keys())}")
            else:
                logger.error(f"❌ Invalid result type: {type(result)}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Fal.ai ERROR: {str(e)}")
            return None