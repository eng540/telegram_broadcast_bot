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
    """مولد الصور الأدبية - يستخدم خلفيات AI أولاً، ثم خلفيات احتياطية حسب المزاج"""
    
    def __init__(self):
        self.output_dir = "/app/data"
        self.template_dir = "/app/templates"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # لوائح ألوان شعرية للخلفيات
        self.color_palettes = {
            "philosophical": ["#1a2a3a", "#0d1b2a", "#2d3748"],  # كحلي → أسود
            "romantic": ["#4a1c40", "#2c0e28", "#5d2a4a"],       # عنابي → بني
            "contemplative": ["#3a4a3a", "#2d3a2d", "#1e281e"],  # أخضر زيتوني
            "melancholic": ["#2d3748", "#1a202c", "#4a5568"],    # رمادي أدبي
        }
        
        # خلفيات احتياطية منظمة حسب المزاج (Unsplash مجانية)
        self.mood_backgrounds = {
            "philosophical": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?q=80&w=1080",  # جبال
                "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?q=80&w=1080",  # غابات
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=1080",  # جبال داكنة
            ],
            "romantic": [
                "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1080",  # سماء وردية
                "https://images.unsplash.com/photo-1534088568595-a066f410bcda?q=80&w=1080",  # غروب
                "https://images.unsplash.com/photo-1518834103329-356dd9a5c6ff?q=80&w=1080",  # عاصفة وردية
            ],
            "contemplative": [
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1080",    # ضباب
                "https://images.unsplash.com/photo-1439066615861-d1af74d74000?q=80&w=1080",  # بحيرة
                "https://images.unsplash.com/photo-1501854140801-50d01698950b?q=80&w=1080",  # غابة ضبابية
            ],
            "melancholic": [
                "https://images.unsplash.com/photo-1518834103329-356dd9a5c6ff?q=80&w=1080",  # عاصفة
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=1080",  # جبال داكنة
                "https://images.unsplash.com/photo-1439066615861-d1af74d74000?q=80&w=1080",  # بحيرة داكنة
            ]
        }
        
        # خلفيات طوارئ عامة (إذا فشلت الخلفيات المحددة)
        self.fallback_backgrounds = [
            "https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1080",
            "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1080",
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?q=80&w=1080",
        ]

    def _detect_mood(self, text: str) -> str:
        """كشف مزاج النص لاختيار الخلفية المناسبة"""
        text_lower = text.lower()
        
        # مفاهيم فلسفية وحكم
        philosophical_keywords = ["الحياة", "الموت", "الزمن", "الحكمة", "الفلسفة", 
                                 "الوجود", "القدر", "النفس", "العقل", "الحق", "السؤال",
                                 "الجواب", "الفكر", "التفكير", "العلم", "المعرفة"]
        
        # مفاهيم رومانسية وعاطفية
        romantic_keywords = ["الحب", "القلب", "الشوق", "الوجد", "العشق", 
                            "الغربة", "الدموع", "الذكرى", "الفراق", "اللقاء",
                            "الهوى", "الغرام", "الوصال", "الهجر", "اللوعة"]
        
        # مفاهيم تأملية
        contemplative_keywords = ["الوحدة", "الصمت", "التأمل", "الروح", "الخلوة",
                                 "الهدوء", "السكينة", "الطمأنينة", "البحث", "السؤال",
                                 "التفكر", "التدبر", "العزلة", "الانسحاب"]
        
        # عد الكلمات
        philo_count = sum(1 for word in philosophical_keywords if word in text_lower)
        romantic_count = sum(1 for word in romantic_keywords if word in text_lower)
        contemplative_count = sum(1 for word in contemplative_keywords if word in text_lower)
        
        # تحديد المزاج الأقوى
        if philo_count > max(romantic_count, contemplative_count) and philo_count > 0:
            return "philosophical"
        elif romantic_count > max(philo_count, contemplative_count) and romantic_count > 0:
            return "romantic"
        elif contemplative_count > max(philo_count, romantic_count) and contemplative_count > 0:
            return "contemplative"
        else:
            # إذا تساوت أو لم توجد كلمات محددة
            text_length = len(text)
            if text_length < 50:
                return "romantic"  # النصوص القصيرة تميل للرومانسية
            elif "لا" in text or "ليس" in text or "إذا" in text:
                return "philosophical"  # النصوص الشرطية فلسفية
            else:
                return "melancholic"  # الافتراضي

    async def _download_background(self, url: str) -> Image.Image:
        """تحميل خلفية من URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        img_data = await response.read()
                        return Image.open(BytesIO(img_data))
                    else:
                        logger.error(f"❌ Failed to download background: HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ فشل تحميل الخلفية {url}: {e}")
        
        # خلفية بديلة حسب اللون
        return Image.new('RGB', (1080, 1440), color='#0d1b2a')

    def _process_background_cinematically(self, bg_image: Image.Image, mood: str) -> Image.Image:
        """
        معالجة سينمائية للخلفية (Apple/Netflix Style)
        Dark center mask + Gaussian blur في الأطراف + Contrast balancing
        """
        try:
            # 1. ضبط الحجم
            bg_image = bg_image.resize((1200, 1600), Image.Resampling.LANCZOS)
            
            # اقتصاص المركز مع ترك مساحة للتدرج
            left = (bg_image.width - 1080) // 2
            top = (bg_image.height - 1440) // 2
            processed = bg_image.crop((left, top, left + 1080, top + 1440))
            
            # 2. Gaussian blur في الأطراف فقط
            blurred = processed.filter(ImageFilter.GaussianBlur(radius=3))
            
            # إنشاء قناع للتدرج من الوضوح في المركز إلى الضبابية في الأطراف
            mask = Image.new('L', (1080, 1440), 0)
            draw = ImageDraw.Draw(mask)
            
            # مركز مائل للأعلى (للمحاذاة الأدبية)
            center_x, center_y = 540, 620
            
            # دائرة مركزية واضحة
            radius_clear = 320
            
            # تدرج للانتقال السلس
            for r in range(radius_clear, 650, 20):
                alpha = int(255 * (1 - ((r - radius_clear) / 330) ** 2))
                if alpha < 0:
                    alpha = 0
                draw.ellipse([center_x-r, center_y-r, center_x+r, center_y+r], 
                            outline=alpha, width=18)
            
            # دمج الصور حسب القناع
            processed = Image.composite(processed, blurred, mask)
            
            # 3. Dark center mask (تأثير Vignette مركّز)
            vignette_color = self._hex_to_rgb(self.color_palettes[mood][0])
            vignette = Image.new('RGB', (1080, 1440), vignette_color)
            vignette_mask = Image.new('L', (1080, 1440), 0)
            vignette_draw = ImageDraw.Draw(vignette_mask)
            
            # تدرج داكن من المركز
            for i in range(0, 550, 15):
                alpha = int(220 * (1 - (i / 550) ** 2))
                vignette_draw.ellipse([center_x-i, center_y-i, center_x+i, center_y+i], 
                                     outline=alpha, width=15)
            
            # تطبيق الـ Vignette بنسبة 20-30% حسب المزاج
            vignette_strength = 0.22 if mood == "romantic" else 0.28
            processed = Image.blend(processed, vignette, vignette_strength)
            
            # 4. Contrast balancing
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.15)  # زيادة طفيفة في التباين
            
            enhancer = ImageEnhance.Brightness(processed)
            brightness_factor = 0.88 if mood == "melancholic" else 0.92
            processed = enhancer.enhance(brightness_factor)  # تقليل السطوع
            
            # 5. إضافة خامة ورق خفيفة (للشعر والنصوص التأملية)
            if mood in ["romantic", "contemplative"]:
                # خفيفة جدًا (3% فقط)
                texture = Image.new('RGB', (1080, 1440), (255, 255, 255))
                texture_draw = ImageDraw.Draw(texture)
                
                # خطوط خفيفة كخامة ورق
                for i in range(0, 1440, 45):
                    texture_draw.line([(0, i), (1080, i)], 
                                     fill=(240, 240, 235, 12), width=1)
                
                processed = Image.blend(processed, texture, 0.03)
            
            return processed
            
        except Exception as e:
            logger.error(f"❌ Failed to process background: {e}")
            # خلفية بسيطة بلون المزاج
            return Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0]))

    def _hex_to_rgb(self, hex_color: str):
        """تحويل hex إلى RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _calculate_typography(self, text: str) -> dict:
        """حساب إعدادات الطباعة الذكية حسب طول النص"""
        text_length = len(text)
        
        # إزالة الأسطر الفارغة للحساب الدقيق
        lines = [line for line in text.split('\n') if line.strip()]
        effective_length = sum(len(line) for line in lines)
        
        if effective_length < 40:        # بيت شعر قصير جداً
            return {
                "font_size": 86,
                "line_height": 1.82,
                "top_offset": 560,       # أعلى قليلاً
                "max_width": 880,
                "padding": "50px 30px"
            }
        elif effective_length < 80:      # بيت شعر أو بيتين
            return {
                "font_size": 72,
                "line_height": 1.85,
                "top_offset": 520,
                "max_width": 850,
                "padding": "50px 30px"
            }
        elif effective_length < 150:     # عدة أبيات
            return {
                "font_size": 64,
                "line_height": 1.88,
                "top_offset": 480,
                "max_width": 820,
                "padding": "50px 30px"
            }
        elif effective_length < 250:     # فقرة متوسطة
            return {
                "font_size": 56,
                "line_height": 1.92,
                "top_offset": 440,
                "max_width": 800,
                "padding": "45px 25px"
            }
        else:                           # نص طويل
            return {
                "font_size": 48,
                "line_height": 1.95,
                "top_offset": 400,
                "max_width": 780,
                "padding": "40px 20px"
            }

    async def render(self, text: str, message_id: int, bg_url: str = None) -> str:
        """الدالة الرئيسية - توليد الصورة الأدبية"""
        
        # 1. كشف مزاج النص
        mood = self._detect_mood(text)
        logger.info(f"📖 مزاج النص: {mood} - AI Background provided: {'Yes' if bg_url else 'No'}")
        
        # 2. اختيار الخلفية (الأولوية لـ AI، ثم خلفية احتياطية حسب المزاج)
        final_bg_url = None
        
        if bg_url and isinstance(bg_url, str) and bg_url.startswith('http'):
            logger.info(f"🎨 Using AI-generated background: {bg_url[:60]}...")
            final_bg_url = bg_url
            bg_source = "AI"
        else:
            # استخدام خلفية احتياطية تناسب المزاج
            if mood in self.mood_backgrounds and self.mood_backgrounds[mood]:
                final_bg_url = random.choice(self.mood_backgrounds[mood])
                logger.info(f"🔄 Using {mood} fallback background (Unsplash)")
                bg_source = f"{mood}_fallback"
            else:
                final_bg_url = random.choice(self.fallback_backgrounds)
                logger.warning(f"⚠️  Using generic fallback background")
                bg_source = "generic_fallback"
        
        # 3. تحميل ومعالجة الخلفية
        try:
            bg_image = await self._download_background(final_bg_url)
            processed_bg = self._process_background_cinematically(bg_image, mood)
            logger.info(f"✅ Background processed successfully ({bg_source})")
        except Exception as e:
            logger.error(f"❌ Failed to process background: {e}")
            # خلفية بسيطة بلون المزاج
            processed_bg = Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0]))
        
        # 4. حفظ الخلفية المعالجة مؤقتاً
        temp_bg_path = os.path.join(self.output_dir, f"processed_bg_{message_id}.jpg")
        try:
            processed_bg.save(temp_bg_path, "JPEG", quality=95)
        except Exception as e:
            logger.error(f"❌ Failed to save processed background: {e}")
            # مسار بديل
            temp_bg_path = os.path.join(self.output_dir, f"simple_bg_{message_id}.jpg")
            processed_bg.save(temp_bg_path, "JPEG", quality=85)
        
        # 5. حساب إعدادات الطباعة
        typo = self._calculate_typography(text)
        
        # 6. توليد HTML مع الخلفية المعالجة
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
                
                /* Gradient overlay سينمائي */
                .cinematic-overlay {{
                    position: absolute;
                    inset: 0;
                    background: radial-gradient(
                        ellipse at center {typo['top_offset']/1440*100}%,
                        rgba(0, 0, 0, 0.18) 0%,
                        rgba(0, 0, 0, 0.42) 45%,
                        rgba(0, 0, 0, 0.78) 100%
                    );
                    z-index: 1;
                }}
                
                /* حاوية النص */
                .literary-text-container {{
                    position: absolute;
                    top: {typo['top_offset']}px;
                    left: 50%;
                    transform: translateX(-50%);
                    width: {typo['max_width']}px;
                    text-align: center;
                    z-index: 2;
                    padding: {typo['padding']};
                }}
                
                /* النص الرئيسي */
                .literary-text {{
                    font-size: {typo['font_size']}px;
                    font-weight: 700;
                    line-height: {typo['line_height']};
                    color: rgba(255, 255, 255, 0.98);
                    text-shadow: 
                        0 3px 12px rgba(0, 0, 0, 0.85),
                        0 1px 4px rgba(0, 0, 0, 0.6);
                    white-space: pre-wrap;
                    letter-spacing: 0.4px;
                    margin: 0;
                    font-family: 'Amiri', serif;
                }}
                
                /* التوقيع */
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
        
        # 7. حفظ HTML مؤقتاً (للتصحيح إذا لزم)
        temp_html_path = os.path.join(self.output_dir, f"debug_{message_id}.html")
        try:
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except:
            pass  # غير مهم إذا فشل
        
        # 8. المسار النهائي للصورة
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        
        # 9. الرندر باستخدام Playwright
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=['--no-sandbox'])
                page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
                await page.set_content(html_content)
                await page.wait_for_timeout(3000)  # وقت للتأكد من تحميل كل شيء
                await page.screenshot(path=output_path, type='jpeg', quality=97)
                await browser.close()
            
            logger.info(f"✅ Image generated successfully: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to render image: {e}")
            # محاولة بديلة
            try:
                # خلفية بسيطة مع نص (بدون Playwright)
                img = Image.new('RGB', (1080, 1440), self._hex_to_rgb(self.color_palettes[mood][0]))
                img.save(output_path, "JPEG", quality=90)
                logger.warning(f"⚠️  Generated simple fallback image")
            except:
                # ملف فارغ كملاذ أخير
                with open(output_path, 'w') as f:
                    f.write('')
        
        # 10. التنظيف - حذف الملفات المؤقتة
        try:
            os.remove(temp_bg_path)
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)
        except Exception as e:
            logger.warning(f"⚠️  Could not clean temp files: {e}")
        
        return output_path