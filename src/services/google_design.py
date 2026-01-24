# --- START OF FILE src/services/google_design.py ---
import logging
import os
import asyncio
import fal_client
import requests
from src.config import settings

logger = logging.getLogger("GoogleDesignService")

class GoogleDesignService:
    def __init__(self):
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY is missing.")
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        # النموذج الأذكى عالميًا للنصوص: Gemini 3 Pro Image
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_masterpiece(self, text: str, message_id: int) -> str:
        """
        Absolute final version: AI acts as elite Arabic Calligrapher, Conceptual Art Director,
        and Visual Storyteller for high-end literary content.
        """
        if not settings.FAL_KEY:
            return None

        logger.info(f"💎 Gemini 3 Pro Crafting Masterpiece for text: {text[:30]}...")

        # --- Ultimate Super-Prompt ---
        prompt = f"""
        ROLE: You are the world's most elite Arabic Calligrapher, Conceptual Art Director,
        and Digital Artist specializing in literary visualization.

        CONTEXT: This text comes from the premium Arabic literary channel "Rwaea3" (t.me/Rwaea3).

        INPUT TEXT:
        "{text}"

        SIGNATURE:
        Small, subtle, elegant "@Rwaea3" integrated organically within the visual design
        (bottom or creatively embedded in elements like decorations, light, or shadows).

        CREATIVE DIRECTIVES:

        1. DEEP TEXT ANALYSIS:
           - Fully read and understand the Arabic text.
           - Extract its literary soul: Sadness, Heroism, Divine/Spiritual, Romance, Wisdom, Nature, Historical depth.
           - Visualize the meaning metaphorically, beyond literal words.

        2. VISUALIZATION & COMPOSITION:
           - The text must be the HERO and fully integrated into the scene.
           - Consider the text as a living architectural element: forming domes, arches, branches, waves, or natural flows.
           - Backgrounds must reflect the literary mood dynamically:
             * Sad/Deep: fog, muted lighting, shadows, textured darkness
             * Divine/Spiritual: celestial glow, rays of light, ethereal clouds
             * Romantic: flowing colors, blooming patterns, soft textures
             * Wisdom/Historical: stone, marble, parchment, ancient libraries
           - Ensure organic integration between text and background, not just overlay.

        3. CALLIGRAPHY:
           - Use majestic Arabic scripts according to mood:
             * Thuluth for grandeur & solemnity
             * Diwani for flow & emotion
             * Naskh for clarity & narration
             * Kufic for historic/strong texts
           - Include Tashkeel (diacritics) artistically.
           - The text should appear as physical material: gold, marble, wood, glowing, carved, or fluid.

        4. LIGHT & COLOR:
           - Cinematic lighting, 8K resolution, Ray Tracing.
           - Colors must enhance mood and readability:
             * Sad: Deep blues, purples, grays
             * Hope/Romance: Golds, soft pinks, emeralds
             * Wisdom: Earthy tones, sepia, bronze
             * Historical: Marble, stone, parchment textures
           - Depth of field: highlight text, add layered realism.

        5. INTEGRITY & QUALITY:
           - Text must be 100% correct in Arabic.
           - Signature "@Rwaea3" must be elegant and part of the environment.
           - Avoid watermarks, logos, or copied elements.
           - Ensure photorealistic textures and cinematic artistic mastery.

        GENERATE THE MASTERPIECE NOW.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 55,   # Maximum detail
                        "guidance_scale": 5.5,       # Strong adherence to prompt while allowing creative freedom
                        "enable_safety_checker": True
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                return await self._download_image(image_url, message_id)

            logger.warning("⚠️ Gemini returned no images.")
            return None

        except Exception as e:
            logger.error(f"❌ Masterpiece Generation Failed: {e}")
            return None

    async def _download_image(self, url: str, message_id: int) -> str:
        try:
            def download():
                response = requests.get(url, timeout=60)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"pro_{message_id}.png")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                return None
            return await asyncio.to_thread(download)
        except Exception as e:
            logger.error(f"Download Error: {e}")
            return None
# --- END OF FILE ---