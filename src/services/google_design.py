# --- START OF FILE src/services/google_design.py ---
import logging
import os
import asyncio
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from src.config import settings

logger = logging.getLogger("NanoBananaPro")

class GoogleDesignService:
    def __init__(self):
        self.client = None
        if settings.GOOGLE_API_KEY:
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            # ✅ THE FIX: استخدام نموذج Imagen 3 المخصص للصور بدلاً من Flash
            self.model_name = "imagen-3.0-generate-001"
        else:
            logger.critical("❌ GOOGLE_API_KEY is missing! Google Design Service Disabled.")

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يستخدم Imagen 3 لتوليد صورة وكتابة النص عليها
        """
        if not self.client:
            return None

        logger.info(f"🍌 Nano Banana Thinking: {text[:30]}...")

        # هندسة الأمر (Prompt) لتفعيل قدرات الكتابة
        prompt = f"""
        Design a professional social media poster.
        
        1. VISUAL STYLE:
           A cinematic, artistic background reflecting the mood of this Arabic text: "{text}".
           Use Islamic geometric patterns, soft lighting, or moody nature.
           
        2. TEXT RENDERING (MANDATORY):
           You MUST write the following Arabic text clearly in the center:
           "{text}"
           
           - Font Style: Elegant Arabic Calligraphy.
           - Color: Gold or White (High contrast against background).
           - Legibility: The text must be 100% readable.
        """

        try:
            # تشغيل الدالة في Thread منفصل
            def call_google():
                # ✅ THE FIX: استخدام generate_images المخصصة لنماذج Imagen
                return self.client.models.generate_images(
                    model=self.model_name,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="3:4",
                        person_generation="DONT_ALLOW",
                        safety_filter_level="BLOCK_MEDIUM_AND_ABOVE"
                    )
                )

            # التنفيذ غير المتزامن
            response = await asyncio.to_thread(call_google)

            # معالجة الرد (Imagen يعيد generated_images مباشرة)
            if response.generated_images:
                image_bytes = response.generated_images[0].image.image_bytes
                
                # حفظ الصورة
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"design_{message_id}.png")
                
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                
                logger.info("✅ Nano Banana (Imagen 3) Design Created Successfully.")
                return output_path
            
            logger.warning("⚠️ No image found in response.")
            return None

        except Exception as e:
            logger.error(f"❌ Nano Banana Failed: {e}")
            return None