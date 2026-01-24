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
        # النموذج المعتمد: Gemini 3 Pro Image (الأذكى في العالم للنصوص)
        self.model_endpoint = "fal-ai/gemini-3-pro-image-preview"

    async def generate_pro_design(self, text: str, message_id: int) -> str:
        """
        Generate a masterpiece design where AI acts as both Art Director and Calligrapher.
        """
        if not settings.FAL_KEY: return None

        logger.info(f"💎 Gemini 3 Pro Dreaming: {text[:30]}...")

        # --- Super-Prompt: هندسة الأوامر المتقدمة ---
        prompt = f"""
        ROLE: You are the world's most renowned Arabic Calligrapher and Surrealist Digital Artist.

        YOUR TASK: Create a breathtaking cinematic poster that visualizes the soul of the text below.

        === THE INPUT ===
        MAIN TEXT (Arabic): "{text}"
        SIGNATURE (Small, Bottom): "@Rwaea3"

        === EXECUTION PROTOCOL ===
        
        1. 🧠 DEEP ANALYSIS (INTERNAL):
           - Analyze the text. Is it Sad? Heroic? Sufi/Divine? Romantic?
           - Visualize a scene that *metaphorically* represents this emotion, not just literally.
           - Example: If text speaks of "hope", visualize light breaking through dark clouds.

        2. 🎨 ARTISTIC DIRECTION (DYNAMIC):
           - Style: Hyper-realistic, 8k, Cinematic Lighting, Ray Tracing.
           - Composition: The Arabic text must be the "Hero" of the image, centered and imposing.
           - Background: Must be atmospheric and moody (e.g., blurry ancient library, desert at twilight, stormy ocean, celestial geometry).
           - Contrast: Text color MUST contrast perfectly with the background (Gold on Dark, Black on Parchment).

        3. ✍️ CALLIGRAPHY ENGINE:
           - Write the MAIN TEXT in the center using majestic Arabic scripts (Thuluth, Diwani, or Royal Naskh).
           - Ensure Diacritics (Tashkeel) are present and artistic.
           - The text should look like it is made of physical material (e.g., liquid gold, carved stone, glowing neon) integrated into the world.
        
        4. 🛡️ INTEGRITY CHECK:
           - The Arabic text must be spelled 100% correctly.
           - The Signature "@Rwaea3" must be small, subtle, and elegant at the bottom center.

        GENERATE THE MASTERPIECE NOW.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3", # الأفضل للجوال
                        "num_inference_steps": 40,    # زدنا الدقة قليلاً لضمان حدة الخط
                        "guidance_scale": 4.5,        # توازن مثالي بين الالتزام بالنص والإبداع الفني
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
        except Exception as e:
            logger.error(f"Download Error: {e}")
            return None