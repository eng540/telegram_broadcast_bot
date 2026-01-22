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
            # ✅ THE FIX: استخدام الموديل الصحيح (Nano Banana Pro) المذكور في الوثائق
            # هذا الموديل يدعم "التفكير" وكتابة النصوص بدقة عالية
            self.model_name = "gemini-3-pro-image-preview"
        else:
            logger.critical("❌ GOOGLE_API_KEY is missing! Google Design Service Disabled.")

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يستخدم Gemini 3 Pro (Nano Banana Pro) لتوليد صورة وكتابة النص عليها
        """
        if not self.client:
            return None

        logger.info(f"🍌 Nano Banana Pro Thinking: {text[:30]}...")

        # هندسة الأمر (Prompt) لتفعيل قدرات الكتابة
        prompt = f"""
        Create a high-fidelity, artistic social media card.
        
        1. THEME:
           A cinematic, deep, and emotional background reflecting this text: "{text}".
           Style: Abstract art, watercolor, or Islamic geometry. Soft, warm lighting.
           
        2. TEXT RENDERING (CRITICAL):
           Render the following Arabic text exactly as written in the center of the image:
           "{text}"
           
           - Font: Calligraphic, Elegant, Arabic style.
           - Color: High contrast (Gold, White, or Black) ensuring 100% readability.
        """

        try:
            # تشغيل الدالة في Thread منفصل
            def call_google():
                # ✅ استخدام generate_content كما في وثائق Nano Banana
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"], # طلب صورة صراحة
                        safety_settings=[ # إعدادات الأمان لضمان عدم حجب القصائد
                            types.SafetySetting(
                                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                threshold="BLOCK_ONLY_HIGH"
                            ),
                            types.SafetySetting(
                                category="HARM_CATEGORY_HATE_SPEECH",
                                threshold="BLOCK_ONLY_HIGH"
                            ),
                        ]
                    )
                )

            # التنفيذ غير المتزامن
            response = await asyncio.to_thread(call_google)

            # معالجة الرد (حسب هيكل Nano Banana في الوثائق)
            for part in response.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    image = Image.open(BytesIO(image_data))
                    
                    # حفظ الصورة
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"design_{message_id}.png")
                    
                    image.save(output_path)
                    logger.info("✅ Nano Banana Pro Design Created Successfully.")
                    return output_path
            
            logger.warning("⚠️ No image found in response.")
            return None

        except Exception as e:
            logger.error(f"❌ Nano Banana Failed: {e}")
            # إذا فشل الموديل الجديد، سيعود النظام تلقائياً لـ HTML Renderer
            return None