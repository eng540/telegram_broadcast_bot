# --- START OF FILE src/services/huggingface_design.py ---
import logging
import os
import asyncio
from huggingface_hub import InferenceClient
from PIL import Image
from io import BytesIO
from src.config import settings

logger = logging.getLogger("HuggingFaceDesignService")

class HuggingFaceDesignService:
    def __init__(self):
        self.client = None
        if settings.HUGGINGFACE_TOKEN:
            self.client = InferenceClient(token=settings.HUGGINGFACE_TOKEN)
            # ✅ النموذج المستخدم: Z-Image-Turbo
            self.model_name = "Tongyi-MAI/Z-Image-Turbo"
        else:
            logger.critical("❌ HUGGINGFACE_TOKEN is missing! Hugging Face Service Disabled.")

    async def generate_design(self, text: str, message_id: int) -> str:
        """يستخدم Z-Image-Turbo لإنشاء تصاميم"""
        if not self.client: return None

        logger.info(f"🎨 Creating Arabic Literary Design: {text[:30]}...")
        prompt = self._create_arabic_prompt(text)
        
        try:
            response = await self._generate_image_async(prompt)
            if response:
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"design_{message_id}.png")
                
                response.save(output_path)
                logger.info("✅ Arabic Literary Design Created Successfully.")
                return output_path
            
            return None
        except Exception as e:
            logger.error(f"❌ Hugging Face Generation Failed: {e}")
            return None

    def _create_arabic_prompt(self, text: str) -> str:
        """إنشاء prompt مخصص"""
        text_type = self._analyze_text_type(text)
        
        # ملاحظة: تمت إضافة توجيهات بالإنجليزية لأن النماذج تفهمها أفضل للوصف البصري
        prompts = {
            "poetry": f"poster design, arabic calligraphy style, text: '{text}', warm colors, golden patterns, cinematic lighting, 8k resolution, highly detailed, islamic art background",
            "wisdom": f"minimalist poster, white background, soft grey gradients, text: '{text}', modern arabic typography, clean, high contrast, 8k",
            "mixed": f"artistic poster, mixed media, arabic aesthetic, text: '{text}', elegant, social media post style, high quality"
        }
        return prompts.get(text_type, prompts["mixed"])

    def _analyze_text_type(self, text: str) -> str:
        word_count = len(text.split())
        if word_count > 6 and ('.' in text or '،' in text): return "poetry"
        elif word_count <= 6: return "wisdom"
        else: return "mixed"

    async def _generate_image_async(self, prompt: str):
        try:
            def generate():
                # تعديل بسيط: استخدام width/height لضمان التوافق
                return self.client.text_to_image(
                    prompt=prompt,
                    model=self.model_name,
                    width=1024,
                    height=1024,
                    # parameters={"num_inference_steps": 8} # اختياري
                )
            return await asyncio.to_thread(generate)
        except Exception as e:
            logger.error(f"❌ Image Generation Error: {e}")
            return None