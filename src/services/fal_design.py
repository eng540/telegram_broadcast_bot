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
        """Generate a creative, intelligent background inspired by Arabic text without writing text on it"""
        
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY not set. Cannot generate background.")
            return None

        logger.info(f"🎨 Generating intelligent background for text: {text[:40]}...")

        # --- PRO Intelligent Dynamic Prompt ---
        prompt = f"""
        ROLE: You are a world-class visual artist and Arabic literary connoisseur.
        
        INPUT (for understanding, NOT to write in the image):
        "{text}"
        
        OBJECTIVE:
        - Create a cinematic, hyper-realistic background inspired by the mood, metaphors, and emotions of the Arabic text.
        - Do NOT write any words, letters, or calligraphy on the image.
        - Avoid human faces, logos, or literal illustrations of the text.
        - The background should be elegant, immersive, and ready for overlaying Arabic text.

        ARTISTIC GUIDELINES:
        1. Analyze the text: what emotions, metaphors, and atmosphere does it convey? (love, nostalgia, spirituality, melancholy, hope, joy)
        2. Translate that understanding into:
           - Color palette (mood colors)
           - Light and shadow
           - Texture and depth
        3. Style:
           - Cinematic, atmospheric, photorealistic, or surreal if fitting
           - 8K quality, professional lighting
           - Soft focus or bokeh where appropriate
           - Composition: balanced with space for text overlay
        4. Forbidden:
           - Any text, calligraphy, logos, or watermarks
           - Direct literal illustration of phrases
           - Faces or figures
           - Generic stock patterns

        EXAMPLES OF THINKING:
        - Text about "longing for home": warm golden light, soft mist, nostalgic atmosphere
        - Text about "spiritual awakening": ethereal light breaking through shadows, gentle glow
        - Text about "lost love": soft melancholic blues, fading textures, reflective water or fog

        FINAL OUTPUT:
        A stunning background image capturing the soul of the Arabic text, elegant, immersive, and text-ready.
        """

        try:
            # Run the FAL model in a thread
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",  # optimized for text overlay
                        "num_inference_steps": 12,    # higher for better quality
                        "guidance_scale": 4.5,        # creative but guided
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
            logger.error(f"❌ Intelligent PRO background generation failed: {e}")
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