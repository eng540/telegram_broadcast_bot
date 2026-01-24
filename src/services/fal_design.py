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
            logger.warning("⚠️ FAL_KEY missing. Service disabled.")
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    def _extract_mood(self, text: str) -> str:
        """
        Map Arabic text to mood keywords (used internally only, not sent as text to AI)
        """
        text = text.lower()
        if any(w in text for w in ['صبح', 'شمس', 'نور', 'أمل', 'سعادة']):
            return "sunrise, hope, pastel, warm light, soft focus"
        elif any(w in text for w in ['ليل', 'ظلام', 'قمر', 'حزن', 'دمع']):
            return "night, melancholic, dark blue, cinematic, stars, moon"
        elif any(w in text for w in ['بحر', 'مطر', 'غيم', 'شجر', 'طبيعة']):
            return "nature, mountains, rivers, cinematic lighting, hyper-realistic"
        else:
            options = [
                "abstract, elegant texture, soft depth of field, gold turquoise beige",
                "vintage, paper texture, cinematic lighting, sepia tones",
                "fluid art, marble texture, clean, modern, white gold grey"
            ]
            return random.choice(options)

    async def generate_background_b64(self, text: str) -> str:
        """
        Generate a background fully inspired by the text without including any letters or words.
        """
        if not settings.FAL_KEY:
            return None

        mood_keywords = self._extract_mood(text)
        logger.info(f"🎨 Mood keywords: {mood_keywords}")

        # --- Prompt STRICTLY BACKGROUND ---
        prompt = f"""
        You are a master visual artist creating a background.
        Focus only on atmosphere, mood, lighting, and composition inspired by {mood_keywords}.
        Create a visually stunning, cinematic background.
        
        STRICT RULES:
        - Absolutely NO text, letters, or calligraphy.
        - No human faces or figures.
        - No logos or watermarks.
        - No literal depiction of text content.
        - Soft focus, bokeh, professional color grading.
        - Balanced composition ready for overlaying text later.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 12,
                        "guidance_scale": 5.0,
                        "enable_safety_checker": True
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                return await self._url_to_base64(image_url)

            logger.warning("⚠️ Model returned no images")
            return None

        except Exception as e:
            logger.error(f"❌ PRO background generation failed: {e}")
            return None

    async def _url_to_base64(self, url: str) -> str:
        """Convert image URL to base64 data URL"""
        try:
            def convert():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    b64_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:{content_type};base64,{b64_data}"
                return None

            return await asyncio.to_thread(convert)
        except Exception as e:
            logger.error(f"❌ Base64 conversion failed: {e}")
            return None