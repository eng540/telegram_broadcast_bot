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
    """
    Upgraded & safe literary background generator.
    Fully compatible with existing project.
    """

    def __init__(self):
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY is missing.")
            return

        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    # ------------------------------------------------------------------
    # Mood Detection (Upgraded but backward-safe)
    # ------------------------------------------------------------------
    def _detect_mood(self, text: str) -> dict:
        text = text.lower()

        # 🌅 Hope / Morning / Joy
        if any(w in text for w in [
            'صبح', 'شمس', 'نور', 'ضياء',
            'أمل', 'سعادة', 'فرح', 'بسمة',
            'زهر', 'ورد', 'جمال'
        ]):
            return {
                "desc": "Soft abstract light gradients, warm uplifting ambiance, gentle flow",
                "colors": "Pastel tones, ivory, light gold, soft blue"
            }

        # 🌑 Sadness / Night / Loss
        if any(w in text for w in [
            'ليل', 'ظلام', 'سهر', 'حزن',
            'ألم', 'فراق', 'دمع', 'وجع', 'موت'
        ]):
            return {
                "desc": "Minimal dark abstract texture, subtle depth, quiet atmosphere",
                "colors": "Muted cold tones, charcoal, deep blue"
            }

        # 🌿 Nature / Calm / Reflection
        if any(w in text for w in [
            'بحر', 'مطر', 'غيم', 'شجر',
            'طبيعة', 'نهر', 'جبل', 'أرض'
        ]):
            return {
                "desc": "Organic abstract textures inspired by nature, soft layers, calm balance",
                "colors": "Earthy neutrals, muted green, soft teal"
            }

        # 🧠 Wisdom / Philosophy (default-safe)
        options = [
            {
                "desc": "Geometric abstract background, elegant rhythm, balanced structure",
                "colors": "Stone gray, beige, soft gold"
            },
            {
                "desc": "Vintage paper-inspired abstract texture, subtle grain, timeless feel",
                "colors": "Sepia, warm brown, off-white"
            },
            {
                "desc": "Fluid abstract marble texture, clean modern aesthetic",
                "colors": "White, light gray, soft gold"
            }
        ]
        return random.choice(options)

    # ------------------------------------------------------------------
    # Image Generation
    # ------------------------------------------------------------------
    async def generate_background_b64(self, text: str) -> str:
        """
        Generate a clean literary background image.
        Text is NEVER sent to the model.
        """

        if not text:
            logger.warning("⚠️ Empty text received.")
            return None

        mood = self._detect_mood(text)
        logger.info(f"🎨 Visual style selected: {mood['desc']}")

        prompt = f"""
        High-quality literary background wallpaper.
        Pure abstract background texture only.

        This image must NOT represent a story, scene, object, or place.
        It is designed solely as a visual backdrop for written text.

        VISUAL STYLE:
        {mood['desc']}

        COLOR PALETTE:
        {mood['colors']}

        COMPOSITION RULES:
        - Minimalist layout
        - Soft focus and smooth transitions
        - Clear negative space for text
        - No focal point

        ABSOLUTE RESTRICTIONS:
        - NO text
        - NO letters
        - NO calligraphy
        - NO symbols
        - NO logos
        - NO watermarks
        - NO people
        - NO faces
        - NO landscape
        - NO sky, clouds, moon
        """

        negative_prompt = """
        text, letters, typography, calligraphy,
        logos, watermarks, symbols,
        people, faces,
        landscape, scenery, sky, clouds, moon,
        photography
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 3,
                        "guidance_scale": 6,
                        "enable_safety_checker": False
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if not result or "images" not in result or not result["images"]:
                logger.error("❌ No image returned from FAL.")
                return None

            image_url = result["images"][0]["url"]
            return await self._url_to_base64(image_url)

        except Exception as e:
            logger.exception(f"❌ Fal.ai generation failed: {e}")
            return None

    # ------------------------------------------------------------------
    # URL → Base64
    # ------------------------------------------------------------------
    async def _url_to_base64(self, url: str) -> str:
        try:
            def convert():
                r = requests.get(url, timeout=30)
                if r.status_code != 200:
                    return None
                encoded = base64.b64encode(r.content).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"

            return await asyncio.to_thread(convert)

        except Exception as e:
            logger.exception(f"❌ Base64 conversion failed: {e}")
            return None