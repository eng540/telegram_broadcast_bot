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
    def __init__(self):
        self.output_dir = "/app/data"
        self.template_dir = "/app/templates"
        os.makedirs(self.output_dir, exist_ok=True)
        self._create_template()
        
        # خلفيات طوارئ مجانية
        self.fallback_backgrounds = [
            "https://images.unsplash.com/photo-1542259681-d2b3c921d71e?q=80&w=1080",
            "https://images.unsplash.com/photo-1518066000714-58c45f1a2c0a?q=80&w=1080",
            "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1080"
        ]

    async def _download_image(self, url: str) -> Image.Image:
        """تحميل صورة من URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        img_data = await response.read()
                        return Image.open(BytesIO(img_data))
        except Exception as e:
            logger.error(f"فشل تحميل الصورة {url}: {e}")
        
        # خلفية سوداء بديلة
        return Image.new('RGB', (1080, 1440), color='black')

    def _process_background(self, bg_image: Image.Image) -> Image.Image:
        """
        معالجة الخلفية بـ Apple/Netflix Style:
        1. مركز داكن (Dark center mask)
        2. Gaussian blur في الأطراف
        3. Contrast balancing
        """
        # 1. تكبير الخلفية قليلاً ثم اقتصاص للتركيز
        original_size = bg_image.size
        enlarged = bg_image.resize((int(original_size[0] * 1.1), int(original_size[1] * 1.1)), 
                                  Image.Resampling.LANCZOS)
        
        # اقتصاص مركز الصورة
        left = (enlarged.width - 1080) // 2
        top = (enlarged.height - 1440) // 2
        cropped = enlarged.crop((left, top, left + 1080, top + 1440))
        
        # 2. تطبيق قناع مركز داكن (Vignette)
        vignette = Image.new('L', (1080, 1440), 255)
        draw = ImageDraw.Draw(vignette)
        
        # رسم تدرج إهليلجي من الأبيض في المركز إلى الأسود في الأطراف
        for i in range(0, 600, 10):
            alpha = int(255 * (1 - (i / 600) ** 2))
            draw.ellipse([540-i, 720-i, 540+i, 720+i], outline=alpha, width=10)
        
        # تطبيق القناع
        dark_overlay = Image.new('RGB', (1080, 1440), (0, 0, 0))
        cropped = Image.blend(cropped, dark_overlay, 0.3)
        
        # 3. Gaussian blur في الأطراف فقط
        blurred = cropped.filter(ImageFilter.GaussianBlur(radius=3))
        
        # قناع للتمويه: مركز واضح، أطراف ضبابية
        mask = Image.new('L', (1080, 1440), 0)
        mask_draw = ImageDraw.Draw(mask)
        
        # رسم دائرة مركزية واضحة
        mask_draw.ellipse([240, 420, 840, 1020], fill=255)
        
        # تدرج للانتقال من الوضوح إلى الضبابية
        for radius in range(300, 540, 20):
            alpha = int(255 * (1 - (radius - 300) / 240))
            mask_draw.ellipse([540-radius, 720-radius, 540+radius, 720+radius], 
                            outline=alpha, width=20)
        
        # دمج الصورتين حسب القناع
        cropped = Image.composite(cropped, blurred, mask)
        
        # 4. تحسين التباين والإضاءة
        enhancer = ImageEnhance.Contrast(cropped)
        cropped = enhancer.enhance(1.2)  # زيادة التباين 20%
        
        enhancer = ImageEnhance.Brightness(cropped)
        cropped = enhancer.enhance(0.9)  # تقليل الإضاءة 10%
        
        return cropped

    def _create_template(self):
        """إنشاء قالب HTML بدون كارد - نص مباشر على الخلفية"""
        os.makedirs(self.template_dir, exist_ok=True)
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Reem+Kufi:wght@500;700&display=swap');
                
                body {
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    height: 1440px;
                    font-family: 'Amiri', serif;
                    background-color: #000;
                    background-image: url('{{ bg_url }}');
                    background-size: cover;
                    background-position: center;
                    position: relative;
                    overflow: hidden;
                }

                .text-container {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 800px;
                    text-align: center;
                    padding: 40px;
                    z-index: 100;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.9;
                    color: rgba(255, 255, 255, 0.98);
                    text-shadow: 
                        0 4px 20px rgba(0, 0, 0, 0.9),
                        0 2px 8px rgba(0, 0, 0, 0.8),
                        0 0 40px rgba(255, 215, 0, 0.25);
                    white-space: pre-wrap;
                    letter-spacing: 0.5px;
                    margin: 0;
                }

                .footer {
                    position: absolute;
                    bottom: 60px;
                    left: 0;
                    right: 0;
                    text-align: center;
                    padding-top: 20px;
                    border-top: 1px solid rgba(255, 255, 255, 0.15);
                    margin: 0 80px;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 26px;
                    color: #ffd700;
                    letter-spacing: 3px;
                    direction: ltr;
                    text-shadow: 
                        0 2px 8px rgba(0, 0, 0, 0.8),
                        0 0 20px rgba(255, 215, 0, 0.4);
                    font-weight: 700;
                }
            </style>
        </head>
        <body>
            <div class="text-container">
                <div class="text-body">{{ text }}</div>
            </div>
            <div class="footer">
                <div class="handle">""" + settings.CHANNEL_HANDLE + """</div>
            </div>
        </body>
        </html>
        """
        
        template_path = os.path.join(self.template_dir, "card.html")
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    async def _process_and_save_background(self, bg_url: str, message_id: int) -> str:
        """معالجة الخلفية وحفظها مؤقتاً"""
        # تحميل الصورة
        bg_image = await self._download_image(bg_url)
        
        # معالجتها
        processed_bg = self._process_background(bg_image)
        
        # حفظها مؤقتاً
        temp_path = os.path.join(self.output_dir, f"bg_{message_id}.jpg")
        processed_bg.save(temp_path, "JPEG", quality=95)
        
        return temp_path

    async def render(self, text: str, message_id: int, bg_url: str = None) -> str:
        # إذا لم توجد خلفية، استخدم خلفية طوارئ
        if not bg_url:
            bg_url = random.choice(self.fallback_backgrounds)
        
        # 1. معالجة الخلفية
        logger.info(f"🎨 معالجة الخلفية لـ message_id: {message_id}")
        try:
            # معالجة الخلفية وحفظها محلياً
            processed_bg_path = await self._process_and_save_background(bg_url, message_id)
            
            # استخدام المسار المحلي للخلفية في HTML
            local_bg_url = f"file://{processed_bg_path}"
        except Exception as e:
            logger.error(f"❌ فشل معالجة الخلفية: {e}")
            local_bg_url = bg_url  # استخدم الرابط الأصلي كبديل

        # 2. حساب حجم الخط
        text_len = len(text)
        if text_len < 50: font_size = 90
        elif text_len < 150: font_size = 75
        elif text_len < 300: font_size = 60
        else: font_size = 50

        # 3. توليد HTML
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(
            text=text, 
            font_size=font_size, 
            bg_url=local_bg_url
        )
        
        # 4. المسار النهائي
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        # 5. رندر باستخدام Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            await page.set_content(html_out)
            await page.wait_for_timeout(2500)  # وقت أكثر للتأكد من تحميل الخلفية
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
        
        # 6. تنظيف الخلفية المؤقتة إذا كانت محلية
        if 'processed_bg_path' in locals():
            try:
                os.remove(processed_bg_path)
            except:
                pass
            
        return output_path