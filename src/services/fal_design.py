import logging
import os
import asyncio
import fal_client
import requests
import base64
import random
from src.config import settings

logger = logging.getLogger("FalDesignService")

class FalDesignService:
    def __init__(self):
        if not settings.FAL_KEY: 
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        # نستخدم Schnell لأنه الأسرع والأرخص للخلفيات
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background_b64(self, text: str) -> str:
        """
        توليد خلفية فنية ذكية مع تشفيرها مباشرة لتجنب مشاكل التحميل
        """
        logger.info(f"🎨 Generating intelligent background for text: {text[:40]}...")

        # --- هندسة الأمر المحسنة (Optimized Prompt) ---
        # قمنا بتبسيط التعليمات ليفهمها نموذج الصور (Flux) بشكل أفضل
        # نركز على "الجو العام" (Atmosphere) ونمنع النص بصرامة
        prompt = f"""
        Cinematic Art Background.
        
        CONTEXT (Do not draw text): "{text[:200]}"
        
        VISUAL STYLE:
        - High-end Abstract Art, Islamic Geometric Patterns, or Moody Nature.
        - Soft Focus, Bokeh Effect, Volumetric Lighting, 8k Resolution.
        - Deep Colors: Midnight Blue, Gold, Emerald, Charcoal.
        
        COMPOSITION:
        - Minimalist center (Negative Space) to allow text overlay later.
        - The image must be a TEXTURE or ATMOSPHERE only.
        
        STRICT NEGATIVE PROMPT (Forbidden):
        - NO TEXT, NO LETTERS, NO CALLIGRAPHY inside the image.
        - NO HUMAN FACES.
        - NO WATERMARKS.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 4,      # ✅ Schnell يعمل بأفضل كفاءة عند 4 خطوات
                        "guidance_scale": 3.5,         # تقليل التوجيه قليلاً لزيادة الإبداع الفني
                        "enable_safety_checker": True
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                # التحويل الفوري إلى Base64 (الحل الجذري للشاشة السوداء)
                return await self._url_to_base64(image_url)

            logger.warning("⚠️ Model returned no images")
            return None

        except Exception as e:
            logger.error(f"❌ Intelligent background generation failed: {e}")
            return None

    async def _url_to_base64(self, url: str) -> str:
        """تحميل الصورة وتحويلها إلى كود Base64 لدمجها في HTML"""
        try:
            def convert():
                # مهلة 30 ثانية للتحميل
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # تحديد نوع المحتوى تلقائياً
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    b64_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:{content_type};base64,{b64_data}"
                return None

            return await asyncio.to_thread(convert)
        except Exception as e:
            logger.error(f"❌ Base64 conversion failed: {e}")
            return None