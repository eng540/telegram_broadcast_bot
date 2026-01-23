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
            # ✅ استخدام FLUX Schnell (مفتوح، سريع، ولا يسبب 403 عادة)
            self.model_name = "black-forest-labs/FLUX.1-schnell"
            self.client = InferenceClient(token=self.token)
        else:
            logger.warning("⚠️ Token Missing.")

    async def generate_design(self, text: str, message_id: int) -> str:
        if not self.client: return None

        logger.info(f"🎨 AI Imagining (FLUX): {text[:30]}...")

        # ترجمة الأمر للإنجليزية لضمان فهم الموديل
        prompt = f"poster design, arabic calligraphy, text concept: '{text}', cinematic lighting, 8k resolution, islamic geometric patterns, masterpiece"

        try:
            def call_api():
                return self.client.text_to_image(
                    prompt=prompt,
                    model=self.model_name
                )

            # مهلة 40 ثانية
            image = await asyncio.wait_for(
                asyncio.to_thread(call_api),
                timeout=40.0
            )
            
            if image:
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"flux_{message_id}.png")
                image.save(output_path)
                logger.info("✅ FLUX Image Generated.")
                return output_path
            
            return None

        except Exception as e:
            # إذا فشل (مثل 403)، يسجل الخطأ ويكمل بسلام
            logger.error(f"❌ AI Error: {e}")
            return None