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

logger = logging.getLogger("LiteraryImageGenerator")

class ImageGenerator:
    """مولد الصور الأدبية الذكي - يدعم AI أولاً، ثم Fallbacks"""
    
    def __init__(self):
        self.output_dir = "/app/data"
        self.template_dir = "/app/templates"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # لوائح ألوان شعرية
        self.color_palettes = {
            "philosophical": ["#1a2a3a", "#0d1b2a", "#2d3748"],
            "romantic": ["#4a1c40", "#2c0e28", "#5d2a4a"],
            "contemplative": ["#3a4a3a", "#2d3a2d", "#1e281e"],
            "melancholic": ["#2d3748", "#1a202c", "#4a5568"],
        }
        
        # خلفيات احتياطية ذكية حسب المزاج
        self.mood_backgrounds = {
            "philosophical": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?q=80&w=1080",
                "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?q=80&w=1080",
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=1080",
            ],
            "romantic": [
                "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1080",
                "https://images.unsplash.com/photo-1534088568595-a066f410bcda?q=80&w=1080",
                "https://images.unsplash.com/photo-1518834103329-356dd9a5c6ff?q=80&w=1080",
            ],
            "contemplative": [
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1080",
                "https://images.unsplash.com/photo-1439066615861-d1af74d74000?q=80&w=1080",
                "https://images.unsplash.com/photo-1501854140801-50d01698950b?q=80&w=1080",
            ],
            "melancholic": [
                "https://images.unsplash.com/photo-1518834103329-356dd9a5c6ff?q=80&w=1080",
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=1080",
                "https://images.unsplash.com/photo-1439066615861-d1af74d74000?q=80&w=1080",
            ]
        }

    def _detect_mood(self, text: str) -> str:
        """كشف مزاج النص بدقة"""
        text_lower = text.lower()
        
        philosophical = ["الحياة", "الموت", "الزمن", "الحكمة", "الفلسفة", 
                        "الوجود", "القدر", "النفس", "العقل", "الحق"]
        romantic = ["الحب", "القلب", "الشوق", "الوجد", "العشق", 
                   "الغربة", "الدموع", "الذكرى", "الفراق"]
        contemplative = ["الوحدة", "الصمت", "التأمل", "الروح", "الهدوء"]
        
        philo_count = sum(1 for word in philosophical if word in text_lower)
        romantic_count = sum(1 for word in romantic if word in text_lower)
        contemplative_count = sum(1 for word in contemplative if word in text_lower)
        
        if philo_count > max(romantic_count, contemplative_count, 0):
            return "philosophical"
        elif romantic_count > max(philo_count, contemplative_count, 0):
            return "romantic"
        elif contemplative_count > max(philo_count, romantic_count, 0):
            return "contemplative"
        else:
            return "melancholic"

    async def _download_background(self, url: str) -> Image.Image:
        """تحميل خلفية من URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        img_data = await response.read()
                        return Image.open(BytesIO(img_data))
                    else:
                        logger.error(f"❌ Download failed: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
        
        # خلفية بديلة بسيطة
        return Image.new('RGB', (1080, 1440), color='#0d1b2a')

    def _process_background(self, bg_image: Image.Image, mood: str) -> Image.Image:
        """معالجة الخلفية سينمائياً"""
        try:
            # 1. تحجيم واقتصاص
            bg_image = bg_image.resize((1200, 1600), Image.Resampling.LANCZOS)
            left = (bg_image.width - 1080) // 2
            top = (bg_image.height - 1440) // 2
            processed = bg_image.crop((left, top, left + 1080, top + 1440))
            
            # 2. تأثير Vignette
            vignette = Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0]))
            processed = Image.blend(processed, vignette, 0.25)
            
            # 3. تحسين التباين والسطوع
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.15)
            
            enhancer = ImageEnhance.Brightness(processed)
            processed = enhancer.enhance(0.92)
            
            return processed
            
        except Exception as e:
            logger.error(f"❌ Background processing error: {e}")
            return Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0]))

    def _hex_to_rgb(self, hex_color: str):
        """تحويل hex إلى RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _calculate_typography(self, text: str) -> dict:
        """حساب إعدادات الطباعة"""
        text_length = len(text)
        
        if text_length < 50:
            return {"font_size": 86, "line_height": 1.82, "top_offset": 560, "max_width": 880}
        elif text_length < 150:
            return {"font_size": 72, "line_height": 1.85, "top_offset": 520, "max_width": 850}
        elif text_length < 300:
            return {"font_size": 64, "line_height": 1.88, "top_offset": 480, "max_width": 820}
        elif text_length < 500:
            return {"font_size": 56, "line_height": 1.92, "top_offset": 440, "max_width": 800}
        else:
            return {"font_size": 48, "line_height": 1.95, "top_offset": 400, "max_width": 780}

    async def _get_final_background(self, text: str, mood: str, provided_bg_url: str = None) -> str:
        """الحصول على الخلفية النهائية (ذكية)"""
        
        # الخيار 1: استخدام الخلفية المقدمة (من AI)
        if provided_bg_url and isinstance(provided_bg_url, str) and provided_bg_url.startswith('http'):
            logger.info(f"✅ Using PROVIDED AI background")
            return provided_bg_url
        
        # الخيار 2: محاولة توليد خلفية AI مباشرة
        try:
            logger.info("🔄 Attempting DIRECT AI generation...")
            from src.services.fal_design import FalDesignService
            
            fal_service = FalDesignService()
            if hasattr(fal_service, 'model_endpoint'):
                ai_bg = await fal_service.generate_background(text)
                if ai_bg and ai_bg.startswith('http'):
                    logger.info(f"✅ DIRECT AI generation SUCCESS")
                    return ai_bg
        except Exception as e:
            logger.warning(f"⚠️  Direct AI failed: {e}")
        
        # الخيار 3: استخدام خلفية احتياطية حسب المزاج
        logger.info(f"🎨 Using {mood} FALLBACK background")
        if mood in self.mood_backgrounds:
            return random.choice(self.mood_backgrounds[mood])
        
        # الخيار 4: خلفية عامة (آخر ملاذ)
        fallbacks = [
            "https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1080",
            "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1080",
        ]
        return random.choice(fallbacks)

    async def render(self, text: str, message_id: int, bg_url: str = None) -> str:
        """الدالة الرئيسية - توليد الصورة"""
        
        # 1. كشف مزاج النص
        mood = self._detect_mood(text)
        logger.info(f"📖 Mood detected: {mood}")
        logger.info(f"📥 Received bg_url: {'Provided' if bg_url else 'None'}")
        
        # 2. الحصول على الخلفية النهائية
        final_bg_url = await self._get_final_background(text, mood, bg_url)
        logger.info(f"🎯 Final background URL: {final_bg_url[:80] if final_bg_url else 'None'}...")
        
        # 3. تحميل ومعالجة الخلفية
        try:
            bg_image = await self._download_background(final_bg_url)
            processed_bg = self._process_background(bg_image, mood)
            
            # حفظ مؤقت
            temp_bg_path = os.path.join(self.output_dir, f"bg_{message_id}.jpg")
            processed_bg.save(temp_bg_path, "JPEG", quality=95)
            
        except Exception as e:
            logger.error(f"❌ Background processing failed: {e}")
            # خلفية بسيطة
            temp_bg_path = os.path.join(self.output_dir, f"simple_bg_{message_id}.jpg")
            Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0])).save(temp_bg_path, "JPEG", quality=90)
        
        # 4. حساب إعدادات النص
        typo = self._calculate_typography(text)
        
        # 5. توليد HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap" rel="stylesheet">
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
                
                .overlay {{
                    position: absolute;
                    inset: 0;
                    background: radial-gradient(
                        ellipse at center 60%,
                        rgba(0,0,0,0.2) 0%,
                        rgba(0,0,0,0.5) 50%,
                        rgba(0,0,0,0.8) 100%
                    );
                    z-index: 1;
                }}
                
                .text-container {{
                    position: absolute;
                    top: {typo['top_offset']}px;
                    left: 50%;
                    transform: translateX(-50%);
                    width: {typo['max_width']}px;
                    text-align: center;
                    z-index: 2;
                    padding: 40px 20px;
                }}
                
                .text {{
                    font-size: {typo['font_size']}px;
                    font-weight: 700;
                    line-height: {typo['line_height']};
                    color: rgba(255,255,255,0.98);
                    text-shadow: 0 3px 12px rgba(0,0,0,0.85);
                    white-space: pre-wrap;
                    margin: 0;
                }}
                
                .signature {{
                    position: absolute;
                    bottom: 50px;
                    left: 0;
                    right: 0;
                    text-align: center;
                    z-index: 2;
                    padding-top: 25px;
                    border-top: 1px solid rgba(255,255,255,0.1);
                    margin: 0 100px;
                }}
                
                .handle {{
                    font-family: 'Amiri', serif;
                    font-size: 24px;
                    color: rgba(255,255,255,0.65);
                    direction: ltr;
                    opacity: 0.7;
                }}
            </style>
        </head>
        <body>
            <div class="overlay"></div>
            <div class="text-container">
                <div class="text">{text}</div>
            </div>
            <div class="signature">
                <div class="handle">{settings.CHANNEL_HANDLE}</div>
            </div>
        </body>
        </html>
        """
        
        # 6. المسار النهائي
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        
        # 7. الرندر باستخدام Playwright
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=['--no-sandbox'])
                page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
                await page.set_content(html_content)
                await page.wait_for_timeout(2000)
                await page.screenshot(path=output_path, type='jpeg', quality=95)
                await browser.close()
        except Exception as e:
            logger.error(f"❌ Playwright failed: {e}")
        
        # 8. تنظيف
        try:
            os.remove(temp_bg_path)
        except:
            pass
        
        return output_path