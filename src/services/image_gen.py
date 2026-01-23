import os
import logging
import random
import asyncio
import aiohttp
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from src.config import settings

logger = logging.getLogger("HtmlRenderer")

class ImageGenerator:
    """الكلاس الرئيسي مع الحفاظ على الاسم القديم للتكامل"""
    
    def __init__(self):
        self.output_dir = "/app/data"
        self.template_dir = "/app/templates"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # لوائح ألوان شعرية للخلفيات
        self.color_palettes = {
            "philosophical": ["#1a2a3a", "#0d1b2a", "#2d3748"],
            "romantic": ["#4a1c40", "#2c0e28", "#5d2a4a"],
            "contemplative": ["#3a4a3a", "#2d3a2d", "#1e281e"],
            "melancholic": ["#2d3748", "#1a202c", "#4a5568"],
        }
        
        # خلفيات طوارئ
        self.fallback_backgrounds = [
            "https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1080",
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?q=80&w=1080",
            "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1080",
        ]

    def _detect_mood(self, text: str) -> str:
        """كشف مزاج النص"""
        text_lower = text.lower()
        philosophical_keywords = ["الحياة", "الموت", "الزمن", "الحكمة", "الفلسفة"]
        romantic_keywords = ["الحب", "القلب", "الشوق", "الوجد", "العشق"]
        
        philo_count = sum(1 for word in philosophical_keywords if word in text_lower)
        romantic_count = sum(1 for word in romantic_keywords if word in text_lower)
        
        if philo_count > romantic_count and philo_count > 0:
            return "philosophical"
        elif romantic_count > philo_count and romantic_count > 0:
            return "romantic"
        elif any(word in text_lower for word in ["الوحدة", "الصمت", "التأمل"]):
            return "contemplative"
        return "melancholic"

    async def _download_background(self, url: str) -> Image.Image:
        """تحميل الخلفية"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        img_data = await response.read()
                        return Image.open(BytesIO(img_data))
        except Exception as e:
            logger.error(f"❌ فشل تحميل الخلفية: {e}")
        return Image.new('RGB', (1080, 1440), color='#0d1b2a')

    def _process_background_cinematically(self, bg_image: Image.Image, mood: str) -> Image.Image:
        """معالجة الخلفية سينمائياً"""
        # 1. ضبط الحجم والاقتصاص
        bg_image = bg_image.resize((1200, 1600), Image.Resampling.LANCZOS)
        left = (bg_image.width - 1080) // 2
        top = (bg_image.height - 1440) // 2
        processed = bg_image.crop((left, top, left + 1080, top + 1440))
        
        # 2. Gaussian blur في الأطراف
        blurred = processed.filter(ImageFilter.GaussianBlur(radius=3))
        
        # إنشاء قناع للتدرج
        mask = Image.new('L', (1080, 1440), 0)
        draw = ImageDraw.Draw(mask)
        center_x, center_y = 540, 650
        
        for r in range(300, 700, 20):
            alpha = int(255 * (1 - ((r - 300) / 400) ** 2))
            if alpha < 0: alpha = 0
            draw.ellipse([center_x-r, center_y-r, center_x+r, center_y+r], 
                        outline=alpha, width=20)
        
        processed = Image.composite(processed, blurred, mask)
        
        # 3. Dark center mask
        vignette = Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0]))
        vignette_mask = Image.new('L', (1080, 1440), 0)
        vignette_draw = ImageDraw.Draw(vignette_mask)
        
        for i in range(0, 600, 15):
            alpha = int(200 * (1 - (i / 600) ** 2))
            vignette_draw.ellipse([center_x-i, center_y-i, center_x+i, center_y+i], 
                                 outline=alpha, width=15)
        
        processed = Image.blend(processed, vignette, 0.25)
        
        # 4. تحسين التباين والسطوع
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(1.12)
        
        enhancer = ImageEnhance.Brightness(processed)
        processed = enhancer.enhance(0.94)
        
        return processed

    def _hex_to_rgb(self, hex_color: str):
        """تحويل hex إلى RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _calculate_typography(self, text: str) -> dict:
        """حساب إعدادات الطباعة"""
        text_length = len(text)
        
        if text_length < 50:
            return {"font_size": 82, "line_height": 1.85, "top_offset": 500, "max_width": 900}
        elif text_length < 150:
            return {"font_size": 68, "line_height": 1.88, "top_offset": 480, "max_width": 850}
        elif text_length < 300:
            return {"font_size": 58, "line_height": 1.9, "top_offset": 450, "max_width": 820}
        else:
            return {"font_size": 52, "line_height": 1.92, "top_offset": 400, "max_width": 800}

    async def render(self, text: str, message_id: int, bg_url: str = None) -> str:
        """الدالة الرئيسية - تحافظ على نفس الاسم"""
        
        # 1. كشف المزاج
        mood = self._detect_mood(text)
        logger.info(f"📖 مزاج النص: {mood}")
        
        # 2. تحميل ومعالجة الخلفية
        if not bg_url:
            bg_url = random.choice(self.fallback_backgrounds)
        
        bg_image = await self._download_background(bg_url)
        processed_bg = self._process_background_cinematically(bg_image, mood)
        
        # 3. حفظ الخلفية مؤقتاً
        temp_bg_path = os.path.join(self.output_dir, f"processed_bg_{message_id}.jpg")
        processed_bg.save(temp_bg_path, "JPEG", quality=95)
        
        # 4. حساب الإعدادات
        typo = self._calculate_typography(text)
        
        # 5. توليد HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Scheherazade+New:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    height: 1440px;
                    background-color: #0d1b2a;
                    background-image: url('file://{temp_bg_path}');
                    background-size: cover;
                    background-position: center;
                    position: relative;
                    font-family: 'Amiri', serif;
                    overflow: hidden;
                }}
                
                .cinematic-overlay {{
                    position: absolute;
                    inset: 0;
                    background: radial-gradient(
                        ellipse at center 65%,
                        rgba(0, 0, 0, 0.15) 0%,
                        rgba(0, 0, 0, 0.45) 50%,
                        rgba(0, 0, 0, 0.85) 100%
                    );
                    z-index: 1;
                }}
                
                .literary-text-container {{
                    position: absolute;
                    top: {typo['top_offset']}px;
                    left: 50%;
                    transform: translateX(-50%);
                    width: {typo['max_width']}px;
                    text-align: center;
                    z-index: 2;
                    padding: 40px 20px;
                }}
                
                .literary-text {{
                    font-size: {typo['font_size']}px;
                    font-weight: 700;
                    line-height: {typo['line_height']};
                    color: rgba(255, 255, 255, 0.98);
                    text-shadow: 0 3px 12px rgba(0, 0, 0, 0.85);
                    white-space: pre-wrap;
                    letter-spacing: 0.4px;
                    margin: 0;
                }}
                
                .literary-signature {{
                    position: absolute;
                    bottom: 50px;
                    left: 0;
                    right: 0;
                    text-align: center;
                    z-index: 2;
                    padding-top: 25px;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                    margin: 0 100px;
                }}
                
                .handle {{
                    font-family: 'Scheherazade New', serif;
                    font-size: 24px;
                    color: rgba(255, 255, 255, 0.65);
                    letter-spacing: 1.5px;
                    direction: ltr;
                    font-weight: 400;
                    opacity: 0.7;
                }}
            </style>
        </head>
        <body>
            <div class="cinematic-overlay"></div>
            <div class="literary-text-container">
                <div class="literary-text">{text}</div>
            </div>
            <div class="literary-signature">
                <div class="handle">{settings.CHANNEL_HANDLE}</div>
            </div>
        </body>
        </html>
        """
        
        # 6. الرندر
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            await page.set_content(html_content)
            await page.wait_for_timeout(3000)
            await page.screenshot(path=output_path, type='jpeg', quality=97)
            await browser.close()
        
        # 7. التنظيف
        try:
            os.remove(temp_bg_path)
        except:
            pass
        
        return output_path