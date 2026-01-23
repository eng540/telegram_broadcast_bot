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
            # ✅ التغيير الاستراتيجي: استخدام SDXL Base 1.0
            # هذا الموديل هو "ملك" الاستقرار والمجانية والجودة العالية
            self.model_name = "stabilityai/stable-diffusion-xl-base-1.0"
            self.client = InferenceClient(token=self.token)
        else:
            logger.warning("⚠️ Token Missing.")

    async def generate_design(self, text: str, message_id: int) -> str:
        if not self.client: return None

        logger.info(f"🎨 AI Imagining (SDXL): {text[:30]}...")

        # تحسين هندسة الأمر ليتناسب مع SDXL
        # يفضل دائماً استخدام وصف "Soft, Cinematic, Arabic Art"
        prompt = f"Islamic art poster, cinematic lighting, soft colors, beige and gold palette, arabic calligraphy concept, masterpiece, 8k resolution, highly detailed background for text: {text}"

        try:
            def call_api():
                return self.client.text_to_image(
                    prompt=prompt,
                    model=self.model_name
                )

            # مهلة 45 ثانية لأن SDXL قد يأخذ وقتاً للإبداع
            image = await asyncio.wait_for(
                asyncio.to_thread(call_api),
                timeout=45.0
            )
            
            if image:
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"sdxl_{message_id}.png")
                image.save(output_path)
                logger.info("✅ SDXL Image Generated Successfully.")
                return output_path
            
            return None

        except Exception as e:
            logger.error(f"❌ AI Error: {e}")
            return None