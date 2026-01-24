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
            logger.warning("⚠️ FAL_KEY not found. Service will be inactive.")
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background_b64(self, text: str) -> str:
        """
        Generate an intelligent, highly creative background based on Arabic text understanding.
        The image will contain NO text and is fully ready for text overlay.
        """

        logger.info(f"🎨 Generating creative background for text: {text[:50]}...")

        # --- Determine artistic style dynamically ---
        styles = [
            "Cinematic, hyper-realistic, 8K, dramatic lighting, volumetric atmosphere",
            "Painterly, surreal, ethereal, dreamy textures, soft glow",
            "Abstract, geometric, inspired by Arabic patterns, mystical details",
            "Fantasy, epic, glowing lights, magical cinematic composition",
            "Minimalist, elegant, color-graded, soft bokeh, atmospheric depth"
        ]
        style_choice = random.choice(styles)

        # --- Dynamic mood and color based on text ---
        mood_palette = self._detect_mood_and_colors(text)

        # --- Construct advanced creative prompt ---
        prompt = f"""
        You are a world-class visual artist who deeply understands Arabic poetry and literature.
        
        IMPORTANT: DO NOT WRITE THE ARABIC TEXT IN THE IMAGE.
        Text for understanding only: "{text}"

        YOUR MISSION:
        Create a highly creative, cinematic background that captures the soul, emotion, and atmosphere of this Arabic text.

        GUIDELINES:
        - No text, letters, human faces, logos, or literal illustration.
        - Focus on mood, atmosphere, metaphorical imagery, and color harmony.
        - Ensure space and contrast for future Arabic calligraphy overlay.

        STYLE: {style_choice}
        MOOD & COLOR PALETTE: {mood_palette['mood']}, {mood_palette['colors']}
        RESOLUTION: Ultra high quality 8K
        TECHNIQUES: Soft focus, bokeh effects, cinematic lighting, professional color grading
        COMPOSITION: Balanced, layered depth, visually stunning

        REMEMBER: You are designing the stage for the Arabic text to shine. Create a masterpiece background.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 25,   # More steps for detail & depth
                        "guidance_scale": 5.5,      # Strong creative guidance
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
            logger.error(f"❌ Creative background generation failed: {e}")
            return None

    def _detect_mood_and_colors(self, text: str) -> dict:
        """Analyze Arabic text and determine mood and color palette for creative design"""
        text = text.lower()

        # Morning / Hope / Joy
        if any(w in text for w in ['صبح', 'شمس', 'نور', 'ضياء', 'أمل', 'سعادة', 'فرح', 'بسمة', 'زهر', 'ورد', 'جمال']):
            return {
                "mood": "Bright, Hopeful, Warm",
                "colors": "Soft pastels, Light Blue, Golden Yellow, White"
            }

        # Night / Sadness / Melancholy
        elif any(w in text for w in ['ليل', 'ظلام', 'سهر', 'قمر', 'حزن', 'ألم', 'فراق', 'دمع', 'هم', 'وجع', 'موت']):
            return {
                "mood": "Dark, Moody, Mysterious",
                "colors": "Deep Blue, Indigo, Black, Silver, Purple"
            }

        # Nature / Calm
        elif any(w in text for w in ['بحر', 'مطر', 'غيم', 'سماء', 'شجر', 'طبيعة', 'نهر', 'جبل', 'أرض']):
            return {
                "mood": "Peaceful, Majestic, Natural",
                "colors": "Green, Earthy Browns, Sky Blue, Teal"
            }

        # Wisdom / Abstract / Default
        else:
            options = [
                {"mood": "Elegant, Sophisticated, Calm", "colors": "Gold, Turquoise, Beige"},
                {"mood": "Vintage, Nostalgic, Cinematic", "colors": "Sepia, Brown, Black"},
                {"mood": "Abstract, Modern, Minimalist", "colors": "White, Grey, Soft Gold"}
            ]
            return random.choice(options)

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