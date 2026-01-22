# --- START OF FILE src/services/huggingface_design.py ---
import logging
import os
import asyncio
from huggingface_hub import InferenceClient
from PIL import Image
from src.config import settings

logger = logging.getLogger("HuggingFaceDesign")

class HuggingFaceDesignService:
    def __init__(self):
        self.token = settings.HUGGINGFACE_TOKEN
        self.client = None
        
        if self.token:
            try:
                self.client = InferenceClient(token=self.token)
                # ✅ استخدام موديل FLUX السريع والقوي جداً
                self.model_name = "black-forest-labs/FLUX.1-schnell"
                logger.info(f"✅ AI Engine Ready: {self.model_name}")
            except Exception as e:
                logger.error(f"❌ Failed to init AI Client: {e}")
        else:
            logger.warning("⚠️ HUGGINGFACE_TOKEN is missing in .env")

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        توليد صورة فنية للنص
        """
        if not self.client:
            logger.warning("⏩ AI Client not ready. Skipping to HTML...")
            return None

        logger.info(f"🎨 AI Imagining: {text[:30]}...")

        # 1. هندسة الأمر (Prompt Engineering)
        # نحول الطلب إلى إنجليزية وصفية لأن الموديل يفهمها بدقة أكبر للرسم
        prompt = f"""
        A cinematic poster design featuring Arabic calligraphy.
        Center text content (concept): "{text}".
        Style: Islamic geometric patterns, golden texture, dark elegant background (navy blue or black), 
        soft volumetric lighting, 8k resolution, photorealistic, masterpiece.
        The text should be integrated artistically.
        """

        try:
            # 2. التوليد (في Thread منفصل لمنع تجميد البوت)
            def call_api():
                return self.client.text_to_image(
                    prompt=prompt,
                    model=self.model_name,
                    # FLUX سريع جداً، 4 خطوات تكفي
                    num_inference_steps=4,
                    guidance_scale=3.5
                )

            # نعطيه مهلة 30 ثانية قبل الاستسلام
            image = await asyncio.wait_for(
                asyncio.to_thread(call_api),
                timeout=30.0
            )
            
            if image:
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"ai_design_{message_id}.png")
                
                image.save(output_path)
                logger.info(f"✅ AI Image Generated: {output_path}")
                return output_path
            
            return None

        except asyncio.TimeoutError:
            logger.error("❌ AI Generation Timed Out (took > 30s).")
            return None
        except Exception as e:
            logger.error(f"❌ AI Generation Failed: {e}")
            return None