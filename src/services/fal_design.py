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
            return
        os.environ["FAL_KEY"] = settings.FAL_KEY
        self.model_endpoint = "fal-ai/flux/schnell"

    async def generate_background_b64(self, text: str) -> str:
        """Generate intelligent background based on Arabic text understanding"""
        
        logger.info(f"🎨 Generating intelligent background for text: {text[:40]}...")

        # --- Intelligent Dynamic Prompt ---
        # Give the AI the text and let it understand and create accordingly
        prompt = f"""
        You are a brilliant visual artist who understands Arabic poetry and literature.
        
        IMPORTANT ARABIC TEXT FOR UNDERSTANDING (do NOT write this text in the image):
        "{text}"
        
        YOUR CREATIVE MISSION:
        Based on your understanding of this Arabic text, create a cinematic background that captures its essence.
        
        HOW TO THINK ABOUT THIS:
        1. Read and deeply understand the Arabic text above.
        2. What emotions does it evoke? (melancholy, joy, love, spirituality, wisdom, nostalgia, hope, longing)
        3. What imagery does it suggest? (metaphorical, not literal)
        4. What atmosphere would complement this text?
        
        CREATIVE GUIDELINES:
        - Create a background, not an illustration of the text
        - Think in terms of mood, atmosphere, and emotion
        - Use color psychology to match the text's feeling
        - Create visual harmony that would make Arabic calligraphy look beautiful on it
        - Consider lighting that enhances readability
        
        ARTISTIC DIRECTION:
        • Style: Cinematic, atmospheric, elegant
        • Quality: 8K resolution, professional lighting
        • Composition: Balanced, with space for text overlay
        • Mood: Let the text guide your emotional choice
        
        TECHNICAL REQUIREMENTS:
        - Ultra high quality background
        - Soft focus or bokeh effect for text readability
        - Professional color grading
        - Balanced contrast for text overlay
        
        ABSOLUTELY FORBIDDEN:
        ✗ NO text, letters, or writing of any kind
        ✗ NO human faces or figures
        ✗ NO logos or watermarks
        ✗ NO direct illustration of the text's literal meaning
        ✗ NO copied or generic patterns
        
        CREATIVE EXAMPLES OF THINKING:
        If the text is about "longing for homeland":
        ❌ Wrong: Paint a map or flag
        ✅ Right: Create a warm, nostalgic golden hour atmosphere with soft focus
        
        If the text is about "spiritual awakening":
        ❌ Wrong: Paint religious symbols
        ✅ Right: Create ethereal light breaking through darkness, subtle glow
        
        If the text is about "lost love":
        ❌ Wrong: Paint broken hearts
        ✅ Right: Create soft, melancholic blue tones with gentle fading
        
        YOUR ARTISTIC PROCESS:
        1. First, understand the soul of this Arabic text
        2. Translate that understanding into color, light, and texture
        3. Create a visual atmosphere that speaks without words
        4. Ensure it serves as a perfect canvas for the text
        
        Remember: You're creating the stage, not the actor. The Arabic text will be the star.
        Create a background so beautiful that the text will feel honored to be placed upon it.
        """

        try:
            def run_fal():
                return fal_client.subscribe(
                    self.model_endpoint,
                    arguments={
                        "prompt": prompt,
                        "image_size": "portrait_4_3",
                        "num_inference_steps": 6,      # Optimal for quality/speed balance
                        "guidance_scale": 4.0,         # Creative but guided
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
            logger.error(f"❌ Intelligent background generation failed: {e}")
            return None

    async def _url_to_base64(self, url: str) -> str:
        """Convert image URL to base64 data URL"""
        try:
            def convert():
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # Detect content type
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    b64_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:{content_type};base64,{b64_data}"
                return None

            return await asyncio.to_thread(convert)
        except Exception as e:
            logger.error(f"❌ Base64 conversion failed: {e}")
            return None