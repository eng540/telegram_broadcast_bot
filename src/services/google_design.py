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
        # نستخدم أقوى نموذج لدى قوقل حالياً
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_pro_design(self, text: str, message_id: int) -> str:
        """
        يرسل النص لـ Google Gemini ويطلب منه تحليله وتصميمه بأسلوب فني حر
        """
        if not settings.FAL_KEY: return None
        
        logger.info(f"💎 Gemini 3 Pro is analyzing context for: {text[:20]}...")

        # --- هندسة البرومبت الاستراتيجية ---
        # هذا البرومبت يترك الحرية للنموذج لفهم النص وتحويله لتصميم بصري
        prompt = f"""
        ACT AS: An elite Arabic Calligrapher and Conceptual Art Director for a high-end literature channel.
        
        INPUT TEXT:
        "{text}"
        
        --- YOUR CREATIVE PROCESS ---
        1. ANALYZE: Read the Arabic text deeply. Understand the hidden emotions, symbolism, and literary essence.
        2. VISUALIZE: Create a background that represents the *soul* of the text, not just the literal words.
           Use your artistic intelligence to decide the mood, colors, lighting, and textures that best fit the text.
        
        --- EXECUTION REQUIREMENTS ---
        1. THE TEXT IS THE HERO: Write the exact Arabic text provided above in the visual center.
        2. CALLIGRAPHY STYLE: Choose the font style that naturally fits the text's mood and literary tone.
        3. INTEGRATION: The text must feel carved, written, or floating within the environment, NOT just pasted on top.
        4. QUALITY: 8k resolution, Cinematic Lighting, Ray Tracing, Photorealistic textures.
        5. LEGIBILITY: The text must be perfectly readable with high contrast against the background.
        
        Generate the Masterpiece.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        # نعطيه وقتاً كافياً للتفكير والإبداع
                        "num_inference_steps": 40, 
                        "guidance_scale": 4.5 
                    },
                    with_logs=True
                )

            result = await asyncio.to_thread(run_fal)

            if result and 'images' in result and len(result['images']) > 0:
                image_url = result['images'][0]['url']
                return await self._download_image(image_url, message_id)

            return None
        except Exception as e:
            logger.error(f"❌ PRO Design Failed: {e}")
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
        except: return None
# --- END OF FILE ---