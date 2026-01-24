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

    async def generate_background_b64(self, text: str) -> str:
        """
        Generate a creative, intelligent background inspired by Arabic text.
        IMPORTANT: No text, letters, or calligraphy should appear in the image.
        """
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY not set. Cannot generate background.")
            return None

        logger.info(f"🎨 Generating intelligent background for text: {text[:40]}...")

        # --- PRO Dynamic Prompt (strictly background) ---
        prompt = f"""
        ROLE: You are a top-tier visual artist.

        INPUT (for understanding only, do NOT include in the image):
        "{text}"

        OBJECTIVE:
        - Create a cinematic, atmospheric, hyper-realistic background inspired by the emotions, mood, and metaphors of the Arabic text.
        - The image must be completely text-free.
        - Do not include letters, calligraphy, logos, watermarks, or human faces.
        - Focus on mood, lighting, color palette, and texture that reflects the text's essence.
        - Make the composition ready for later text overlay.

        STYLE GUIDELINES:
        - Cinematic, professional, 8K resolution
        - Soft focus or bokeh for text readability
        - Balanced color grading and lighting
        - Immersive, elegant, visually harmonious

        FORBIDDEN:
        ✗ Text, letters, or calligraphy
        ✗ Faces, figures, or identifiable humans
        ✗ Logos, watermarks, or stock patterns
        ✗ Literal depiction of the text
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 12,
                        "guidance_scale": 4.5,
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