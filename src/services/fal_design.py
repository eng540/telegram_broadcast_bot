# --- START OF FILE src/services/fal_design.py ---
import logging
import os
import asyncio
import fal_client
from src.config import settings

logger = logging.getLogger("FalAI_Design")

class FalDesignService:
    def __init__(self):
        self.api_key = settings.FAL_KEY
        if self.api_key:
            # إعداد المفتاح كما تطلب الوثائق
            os.environ["FAL_KEY"] = self.api_key
            # سنستخدم موديل FLUX Schnell للتوليد السريع
            self.model_path = "fal-ai/flux/schnell"
        else:
            logger.critical("❌ FAL_KEY is missing! Service disabled.")

    async def generate_design(self, text: str, message_id: int) -> str:
        if not self.api_key: return None

        logger.info(f"🎨 Fal.ai Generating: {text[:30]}...")

        # ترجمة وهندسة الأمر (Prompt)
        prompt = f"""
        A cinematic poster, arabic calligraphy art, text concept: "{text}".
        Style: Islamic geometric patterns, golden ornate background, soft volumetric lighting, 
        8k resolution, masterpiece, intricate details.
        """

        try:
            # دالة الاتصال بـ fal.ai
            # نستخدم subscribe كما هو مفضل في الوثائق للحصول على التحديثات
            def call_fal():
                handler = fal_client.submit(
                    self.model_path,
                    arguments={
                        "prompt": prompt,
                        "image_size": "landscape_4_3", # [cite: 13]
                        "num_inference_steps": 4,     # Schnell سريع جداً
                        "safety_tolerance": "2"       # [cite: 5]
                    },
                )
                # الانتظار للحصول على النتيجة
                return handler.get()

            # تنفيذ الطلب في Thread منفصل
            result = await asyncio.to_thread(call_fal)

            # استخراج رابط الصورة من النتيجة [cite: 11]
            if result and "images" in result and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]
                
                # تحميل الصورة وحفظها
                import requests
                response = await asyncio.to_thread(requests.get, image_url)
                
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"fal_{message_id}.jpg")
                    
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    
                    logger.info("✅ Fal.ai Image Created Successfully.")
                    return output_path
            
            logger.error(f"⚠️ Unexpected response format: {result}")
            return None

        except Exception as e:
            logger.error(f"❌ Fal.ai Error: {e}")
            return None