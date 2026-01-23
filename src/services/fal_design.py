import logging
import os
import asyncio
import fal_client
import requests
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY:
            logger.critical("❌ FAL_KEY is missing!")
            self.client_ready = False
            return
        
        # إعداد المفتاح
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.client_ready = True
        
        # ✅ استخدام النموذج الذي طلبته (Gemini 3 Pro Image)
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يرسل النص لـ Fal.ai ليقوم برسمه وكتابته في آن واحد
        """
        if not self.client_ready: return None

        logger.info(f"🎨 Fal.ai (Gemini 3) is working on: {text[:30]}...")
        
        # هندسة الأمر (Prompt Engineering) لضمان كتابة النص
        prompt = f"""
        Create a high-quality, cinematic poster.
        
        1. VISUALS: An artistic background reflecting the mood of this text: "{text}".
           (Style: Islamic Art, Abstract, or Moody Nature. Soft lighting).
        
        2. TEXT (CRITICAL):
           You MUST write the following Arabic text clearly in the center of the image:
           "{text}"
           
           - Font: Elegant Arabic Calligraphy.
           - Color: Gold or White (High contrast).
           - The text must be 100% legible.
        """

        try:
            # دالة الاتصال (Sync wrapped in Async)
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3", # مقاس الجوال
                        # إعدادات إضافية لضمان الجودة
                        "num_inference_steps": 30,
                        "guidance_scale": 3.5
                    },
                    with_logs=True
                )

            # التنفيذ
            result = await asyncio.to_thread(run_fal)
            
            # استخراج الصورة
            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                logger.info(f"✅ Fal.ai Image Generated: {image_url}")
                
                # تحميل الصورة للسيرفر
                return await self._download_image(image_url, message_id)
            
            logger.warning("⚠️ Fal.ai returned no images.")
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Generation Failed: {e}")
            return None

    async def _download_image(self, url: str, message_id: int) -> str:
        try:
            def download():
                response = requests.get(url, timeout=60)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"design_{message_id}.png")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                return None

            return await asyncio.to_thread(download)
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None