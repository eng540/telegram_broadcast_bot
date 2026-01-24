import logging
import os
import asyncio
import fal_client
import requests
from src.config import settings

logger = logging.getLogger("GoogleDesignService")

class GoogleDesignService:
    """
    Professional service to generate Arabic literary visual designs using Google Gemini 3 Pro.
    Includes full creative prompt, signature, cinematic quality, and calligraphy integration.
    """

    def __init__(self):
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY is missing. Google Gemini will not work.")
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"
        logger.info("✅ GoogleDesignService initialized with Gemini 3 Pro.")

    async def generate_pro_design(self, text: str, message_id: int) -> str:
        """
        Generate a high-end cinematic Arabic calligraphy design from text.
        Includes signature, deep text analysis, calligraphy, and integrated background.
        """
        if not settings.FAL_KEY:
            return None

        logger.info(f"💎 Generating Pro Design for text: {text[:50]}...")

        # --- Ultimate Super-Prompt ---
        prompt = f"""
        ROLE: You are the world's most renowned Arabic Calligrapher and Surrealist Digital Artist.

        YOUR TASK: Transform the Arabic literary text below into a cinematic, high-end visual masterpiece.

        === INPUT TEXT ===
        MAIN TEXT: "{text}"
        SIGNATURE (small, elegant, bottom center): "روائع من الأدب العربي | @Rwaea3"

        === CREATIVE INSTRUCTIONS ===

        1. DEEP TEXT ANALYSIS:
           - Detect the emotional core: Sadness, Hope, Sufism, Romance, Heroism, Wisdom.
           - Visualize metaphors, not just literal words.
           - The image must *feel* the text before reading it.

        2. CALLIGRAPHY:
           - Choose script matching the mood: Thuluth for majesty, Diwani for emotion, Naskh for prose, Kufic for historical.
           - Include full diacritics artistically.
           - Make text appear material: liquid gold, carved stone, glowing neon.
           - Integrate text organically with the background (not pasted on top).

        3. BACKGROUND & ATMOSPHERE:
           - Match the theme: foggy golden light for mystical, flowers for romance, marble/ancient textures for wisdom, historical sites for heritage.
           - Cinematic lighting, depth, shadows, rays, and realistic textures.
           - Text must remain legible and prominent.

        4. COLOR & MOOD:
           - Emotional palette: Blue/Purple for sorrow, Gold/Amber for hope, Earth tones for wisdom, Pink/Crimson for romance.
           - Harmonize colors with text visibility.

        5. SIGNATURE & COPYRIGHT:
           - Always include signature: "روائع من الأدب العربي | @Rwaea3".
           - Signature should be subtle, elegant, and integrated into the design.

        6. OUTPUT REQUIREMENTS:
           - Resolution: 8K+ portrait_4_3
           - Cinematic quality, ray tracing, photorealistic textures
           - Layered depth and detail, visually immersive
           - Ready for professional publication

        GENERATE THE MASTERPIECE NOW.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 50,  # high detail
                        "guidance_scale": 5.0,      # balance creativity & adherence
                        "enable_safety_checker": True
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and "images" in result and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]
                return await self._download_image(image_url, message_id)

            logger.warning("⚠️ Gemini returned no images.")
            return None

        except Exception as e:
            logger.error(f"❌ PRO Design generation failed: {e}")
            return None

    async def _download_image(self, url: str, message_id: int) -> str:
        """
        Download the generated image and save locally.
        """
        try:
            def download():
                response = requests.get(url, timeout=60)
                if response.status_code == 200:
                    output_dir = "/app/data"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"pro_{message_id}.png")
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return output_path
                return None
            return await asyncio.to_thread(download)
        except Exception as e:
            logger.error(f"❌ Download Error: {e}")
            return None