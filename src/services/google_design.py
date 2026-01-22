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
            # استخدام العميل الجديد حسب الوثائق
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            # النموذج الأقوى (Nano Banana Pro)
            self.model_name = "gemini-2.0-flash-exp" # يمكن تغييرها لـ gemini-3-pro-image-preview عند توفره للعامة
        else:
            logger.critical("❌ GOOGLE_API_KEY is missing! Google Design Service Disabled.")

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يستخدم Nano Banana Pro لتوليد صورة وكتابة النص عليها
        """
        if not self.client:
            return None

        logger.info(f"🍌 Nano Banana Thinking: {text[:30]}...")

        # هندسة الأمر (Prompt) لتفعيل قدرات الكتابة
        prompt = f"""
        Create a professional, high-resolution poster (2K resolution).
        
        1. VISUAL STYLE:
           A cinematic, artistic background reflecting the mood of this text: "{text}".
           Use Islamic geometric patterns, soft lighting, or moody nature.
           
        2. TEXT RENDERING (MANDATORY):
           You MUST write the following Arabic text clearly in the center:
           "{text}"
           
           - Font Style: Elegant Arabic Calligraphy (Thuluth or Diwani).
           - Color: Gold or White (High contrast against background).
           - Legibility: The text must be 100% readable and correct.
        """

        try:
            # تشغيل الدالة في Thread منفصل لأن المكتبة الجديدة قد تكون متزامنة
            def call_google():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_config=types.ImageConfig(
                            aspect_ratio="3:4",
                            # image_size="2K" # ملاحظة: بعض النماذج التجريبية قد لا تدعم هذا الباراميتر بعد، يمكن تفعيله لاحقاً
                        )
                    )
                )

            # التنفيذ غير المتزامن
            response = await asyncio.to_thread(call_google)

            # معالجة الرد
            # في التحديثات الأخيرة قد يكون الرد في parts أو مباشرة
            if hasattr(response, 'parts'):
                parts = response.parts
            else:
                parts = [] # Fallback logic

            for part in parts:
                if part.inline_data:
                    # تحويل البيانات الخام إلى صورة
                    image_data = part.inline_data.data 
                    image = Image.open(BytesIO(image_data))
                    
                    # حفظ الصورة
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"design_{message_id}.png")
                    
                    image.save(output_path)
                    logger.info("✅ Nano Banana Design Created Successfully.")
                    return output_path
            
            logger.warning("⚠️ No image found in response.")
            return None

        except Exception as e:
            logger.error(f"❌ Nano Banana Failed: {e}")
            return None