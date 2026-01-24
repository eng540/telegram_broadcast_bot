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
    Professional literary background generator.
    Compatible with telegram_broadcast_bot project.
    """

    def __init__(self):
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY not found in settings.")
            return

        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    def _detect_mood(self, text: str) -> dict:
        """
        Simple but effective mood detection.
        Maps text to visual style & color palette.
        """

        text = text.lower()

        # Joy / Hope / Morning
        if any(w in text for w in [
            'أمل', 'فرح', 'نور', 'بسمة', 'زهر', 'تفاءل'
        ]):
            return {
                "style": "Soft abstract gradients, smooth flow",
                "colors": "Warm pastel tones, ivory, light gold",
                "atmosphere": "Uplifting, calm, dreamy"
            }

        # Sadness / Night / Loss
        if any(w in text for w in [
            'حزن', 'فراق', 'ألم', 'وجع', 'وحدة', 'ليل'
        ]):
            return {
                "style": "Minimal dark abstract texture",
                "colors": "Muted cold tones, charcoal, deep blue",
                "atmosphere": "Quiet, introspective"
            }

        # Thought / Philosophy
        if any(w in text for w in [
            'فكرة', 'وجود', 'معنى', 'تأمل', 'حكمة'
        ]):
            return {
                "style": "Geometric minimal abstraction",
                "colors": "Neutral stone tones, soft gray",
                "atmosphere": "Balanced, reflective"
            }

        # Rebellion / Intensity
        if any(w in text for w in [
            'ثورة', 'صرخة', 'كسر', 'تحدي'
        ]):
            return {
                "style": "Bold abstract composition",
                "colors": "High contrast warm tones",
                "atmosphere": "Dynamic, powerful"
            }

        # Neutral fallback (diverse styles)
        choices = [
            {
                "style": "Clean modern abstract background",
                "colors": "Soft neutral palette",
                "atmosphere": "Timeless, adaptable"
            },
            {
                "style": "Subtle organic abstract texture",
                "colors": "Warm beige, off-white",
                "atmosphere": "Gentle, unobtrusive"
            },
            {
                "style": "Minimal flowing abstraction",
                "colors": "Balanced muted tones",
                "atmosphere": "Quiet, elegant"
            }
        ]
        return random.choice(choices)

    async def generate_background_b64(self, text: str) -> str:
        """Generate a professional background image from text"""

        if not text:
            logger.warning("⚠️ Empty text provided.")
            return None

        mood = self._detect_mood(text)
        logger.info(f"🎨 Visual Mood: {mood['atmosphere']}")

        prompt = f"""
        High-end literary background wallpaper.
        Pure abstract background texture only.

        This image must NOT represent a scene, object, or story.
        It exists only as visual support for text.

        STYLE: {mood['style']}
        COLORS: {mood['colors']}
        MOOD: {mood['atmosphere']}

        Composition:
        - Minimalist layout
        - Clear negative space for text
        - No focal point

        ABSOLUTE RESTRICTIONS:
        No text, letters, calligraphy,
        symbols, logos, watermarks,
        people, faces, landscapes, skies.
        """

        negative_prompt = """
        text, letters, typography, calligraphy,
        logos, watermarks, symbols,
        people, faces, landscapes, sky, clouds,
        photography
        """

        try:
            def call_fal():
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

            result = await asyncio.to_thread(call_fal)

            if not result or "images" not in result or len(result["images"]) == 0:
                logger.error("❌ FAL returned no images.")
                return None

            image_url = result["images"][0]["url"]
            return await self._url_to_base64(image_url)

        except Exception as e:
            logger.exception(f"❌ FAL generation failed: {e}")
            return None

    async def _url_to_base64(self, url: str) -> str:
        try:
            def fetch():
                r = requests.get(url, timeout=30)
                if r.status_code != 200:
                    return None
                return base64.b64encode(r.content).decode("utf-8")
            b64 = await asyncio.to_thread(fetch)
            return f"data:image/jpeg;base64,{b64}" if b64 else None

        except Exception as e:
            logger.exception(f"❌ Base64 conversion failed: {e}")
            return None