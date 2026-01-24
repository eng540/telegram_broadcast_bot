import logging
import os
import asyncio
import fal_client
import requests
import base64
import random
from src.config import settings

logger = logging.getLogger("FalDesignPROService")

class FalDesignPROService:
    def __init__(self):
        if not settings.FAL_KEY:
            logger.warning("⚠️ FAL_KEY not found. PRO service inactive.")
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_pro_background_b64(self, text: str) -> str:
        """
        Generate a highly creative, layered, cinematic background inspired by Arabic text.
        NO text in image. Optimized for later Arabic calligraphy overlay.
        """

        logger.info(f"🎨 PRO background generation for text: {text[:50]}...")

        # --- Artistic Styles for PRO ---
        pro_styles = [
            "Cinematic, hyper-realistic, 8K, volumetric lighting, layered depth, mystical atmosphere",
            "Painterly, ethereal, dreamy, soft glowing textures, magical bokeh",
            "Abstract, surreal, inspired by Arabic geometric and calligraphic motifs, elegant color harmony",
            "Epic fantasy, cinematic lighting, dramatic shadows, glowing particles, layered composition",
            "Minimalist, professional, subtle gradient overlays, soft depth, atmospheric focus"
        ]
        style_choice = random.choice(pro_styles)

        # --- Mood & Color Palette ---
        mood_palette = self._detect_pro_mood_and_colors(text)

        # --- Advanced PRO Prompt ---
        prompt = f"""
        You are a world-class digital artist and Arabic poetry interpreter.

        IMPORTANT: DO NOT WRITE THE TEXT IN THE IMAGE. 
        Text is for inspiration only: "{text}"

        YOUR TASK:
        - Create an ultra-creative cinematic background inspired by the emotions, imagery, and concepts of the text.
        - Include metaphorical visual elements, layered composition, and depth.
        - Use lighting, shadows, color grading, and subtle textures to convey mood.
        - Prepare the background for future Arabic calligraphy overlay: high contrast, soft focus, harmonious color palette.
        - You may use abstract shapes, soft glowing particles, architectural or natural forms as metaphorical elements.
        - Add a sense of motion or dynamism to make it feel alive.

        STYLE: {style_choice}
        MOOD & COLORS: {mood_palette['mood']}, {mood_palette['colors']}
        RESOLUTION: 8K
        INFERENCE STEPS: High detail for layered depth
        TECHNIQUES: Volumetric lighting, bokeh, soft glows, cinematic shadows, layered textures
        COMPOSITION: Balanced, visually stunning, deep foreground and background
        REMEMBER: Create a masterpiece stage for Arabic text. Text will be the hero later.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 35,   # Higher for PRO depth
                        "guidance_scale": 6.0,      # Strong artistic guidance
                        "enable_safety_checker": True
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                return await self._url_to_base64(image_url)

            logger.warning("⚠️ PRO model returned no images")
            return None

        except Exception as e:
            logger.error(f"❌ PRO background generation failed: {e}")
            return None

    def _detect_pro_mood_and_colors(self, text: str) -> dict:
        """Determine mood and color palette for PRO design based on Arabic text"""
        text = text.lower()

        # Bright / Hope / Joy
        if any(w in text for w in ['صبح', 'شمس', 'نور', 'أمل', 'سعادة', 'فرح', 'بسمة']):
            return {"mood": "Bright, Uplifting, Hopeful", "colors": "Gold, Light Blue, White, Soft Yellow"}

        # Dark / Melancholy / Sad
        elif any(w in text for w in ['ليل', 'ظلام', 'حزن', 'ألم', 'فراق', 'دمع', 'هم', 'وجع']):
            return {"mood": "Dark, Mysterious, Emotional", "colors": "Indigo, Deep Blue, Silver, Black, Violet"}

        # Nature / Calm / Serenity
        elif any(w in text for w in ['بحر', 'مطر', 'غيم', 'شجر', 'طبيعة', 'نهر', 'جبل']):
            return {"mood": "Calm, Majestic, Natural", "colors": "Green, Teal, Earthy Browns, Sky Blue"}

        # Wisdom / Spiritual / Abstract (Default)
        else:
            options = [
                {"mood": "Elegant, Sophisticated, Calm", "colors": "Gold, Turquoise, Beige"},
                {"mood": "Mystical, Surreal, Dreamy", "colors": "Purple, Indigo, Soft White"},
                {"mood": "Abstract, Modern, Minimalist", "colors": "Grey, White, Soft Gold"}
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
            logger.error(f"❌ PRO Base64 conversion failed: {e}")
            return None