# --- START OF FILE src/services/huggingface_design.py ---
import logging
import os
import asyncio
from huggingface_hub import InferenceClient
from PIL import Image
import io
from src.config import settings

logger = logging.getLogger("HuggingFaceDesignService")

class HuggingFaceDesignService:
    def __init__(self):
        self.token = settings.HUGGINGFACE_TOKEN
        if self.token:
            # استخدام الموديل الأكثر استقراراً حالياً للتصاميم الفنية
            self.model_name = "black-forest-labs/FLUX.1-schnell" 
            self.client = InferenceClient(token=self.token)
        else:
            self.client = None
            logger.critical("❌ HUGGINGFACE_TOKEN IS MISSING!")

    async def generate_design(self, text: str, message_id: int) -> str:
        if not self.client: return None

        logger.info(f"🎨 AI is imagining: {text[:30]}...")
        
        # هندسة الأمر بالإنجليزية (لأن الموديل يفهمها بشكل أدق في التصميم)
        prompt = f"Calligraphic Arabic poetry poster, beautiful background, artistic, elegant, high resolution, centered text: {text}"

        try:
            def call_api():
                # طلب الصورة مع تحديد الأبعاد
                return self.client.text_to_image(
                    prompt=prompt,
                    model=self.model_name
                )

            # تنفيذ الطلب مع "مهلة زمنية" أطول
            image = await asyncio.to_thread(call_api)
            
            if image:
                output_dir = "/app/data"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"design_{message_id}.png")
                
                # التأكد من حفظ الصورة بشكل سليم
                image.save(output_path)
                logger.info(f"✅ AI Design Saved: {output_path}")
                return output_path
            
            return None

        except Exception as e:
            logger.error(f"❌ AI Generation Failed: {e}")
            return None