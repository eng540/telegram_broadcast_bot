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
            return
        
        # إعداد المفتاح بيئياً للمكتبة
        os.environ["FAL_KEY"] = settings.FAL_KEY
        
        # نستخدم أقوى نموذج متاح حالياً (Ultra)
        self.model_endpoint = "fal-ai/flux-pro/v1.1-ultra"

    async def generate_design(self, text: str, message_id: int) -> str:
        """
        يرسل النص لـ Fal.ai (Flux Pro) لتصميم بطاقة
        """
        logger.info(f"🎨 Fal.ai (Flux) is painting: {text[:30]}...")
        
        # هندسة الأمر (Prompt Engineering)
        # نطلب منه كتابة النص العربي بوضوح في المنتصف
        prompt = f"""
        A high-end, cinematic typography poster.
        
        Center Subject: The following Arabic text written clearly in elegant calligraphy:
        "{text}"
        
        Background: Artistic, moody, soft lighting, minimal distractions, 8k resolution, masterpiece.
        Style: Editorial photography, Islamic art influence, golden ratio.
        The text must be legible, sharp, and high contrast against the background.
        """

        try:
            # دالة الاتصال (نضعها في دالة منفصلة لتشغيلها بشكل غير متزامن)
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3", # مقاس مناسب للجوال
                        "safety_tolerance": "2",      # سماحية متوسطة
                        "num_inference_steps": 28,
                        "guidance_scale": 3.5
                    },
                    with_logs=True
                )

            # التنفيذ في الخلفية (Thread) لمنع تجميد البوت
            result = await asyncio.to_thread(run_fal)
            
            # استخراج رابط الصورة
            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                logger.info(f"✅ Fal.ai Image Generated: {image_url}")
                
                # تحميل الصورة وحفظها محلياً
                return await self._download_image(image_url, message_id)
            
            logger.warning("⚠️ Fal.ai returned no images.")
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Generation Failed: {e}")
            return None

    async def _download_image(self, url: str, message_id: int) -> str:
        try:
            def download():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"design_{message_id}.jpg")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                return None

            return await asyncio.to_thread(download)
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None