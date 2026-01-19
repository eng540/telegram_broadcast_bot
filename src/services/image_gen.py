import os
import logging
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from src.config import settings

logger = logging.getLogger("HtmlRenderer")
logger.setLevel(logging.INFO)

# استخدم هذا الخط - أجمل للشعر العربي
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"

class ImageGenerator:
    def __init__(self):
        """تهيئة مولد الصور بتصميم ثابت ومتسق"""
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        self.font_path = Path(self.assets_dir) / "amiri.ttf"
        
        # إنشاء المجلدات
        for directory in [self.output_dir, self.assets_dir, self.template_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self._ensure_font()
        self._create_fixed_template()  # تصميم ثابت
        
        # أبعاد ثابتة لجميع الصور
        self.WIDTH = 1080
        self.HEIGHT = 1350

    def _ensure_font(self):
        """التأكد من وجود الخط"""
        if not self.font_path.exists() or self.font_path.stat().st_size < 50000:
            try:
                logger.info("📥 جاري تحميل الخط العربي...")
                urllib.request.urlretrieve(FONT_URL, str(self.font_path))
                logger.info(f"✅ تم تحميل الخط: {self.font_path}")
            except Exception as e:
                logger.error(f"❌ فشل تحميل الخط: {e}")

    def _create_fixed_template(self):
        """إنشاء قالب ثابت الأبعاد مع تصميم متسق"""
        html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بطاقة أدبية</title>
    <style>
        /* الخط الثابت */
        @font-face {
            font-family: 'Amiri';
            src: url('file:///app/assets/amiri.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        
        /* إعادة الضبط */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        /* الجسم - أبعاد ثابتة */
        body {
            width: 1080px;
            height: 1350px;
            margin: 0;
            padding: 0;
            background: #ffffff;
            font-family: 'Amiri', serif;
            color: #2c1e18;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        /* الهيدر الثابت */
        .header {
            height: 120px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            padding-top: 30px;
        }
        
        .header-line {
            width: 400px;
            height: 2px;
            background: linear-gradient(90deg, transparent, #bcaaa4, transparent);
        }
        
        /* المساحة الرئيسية - ثابتة الطول */
        .main-area {
            flex: 1;
            width: 100%;
            padding: 0 80px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .text-container {
            width: 100%;
            max-width: 900px;
            text-align: center;
        }
        
        .text-content {
            font-size: {{ font_size }}px;
            font-weight: normal;
            line-height: 2.0;
            white-space: pre-wrap;
            word-wrap: break-word;
            text-shadow: 0.5px 0.5px 0.5px rgba(0, 0, 0, 0.1);
            padding: 20px;
        }
        
        /* الفوتر الثابت */
        .footer {
            height: 220px;
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding-bottom: 40px;
        }
        
        .footer-divider {
            width: 500px;
            height: 1px;
            background: #d7ccc8;
            margin-bottom: 25px;
            position: relative;
        }
        
        .footer-divider::before {
            content: "❁";
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 0 15px;
            color: #8d6e63;
            font-size: 20px;
        }
        
        .channel-name {
            font-size: 32px;
            font-weight: bold;
            color: #3e2723;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }
        
        .channel-handle {
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 22px;
            color: #0088cc;
            font-weight: 600;
            direction: ltr;
            background: #f8f8f8;
            padding: 10px 30px;
            border-radius: 50px;
            border: 1px solid #e0e0e0;
        }
        
        /* ضمان عدم التجاوز */
        .overflow-guard {
            max-height: 900px;
            overflow-y: auto;
            -ms-overflow-style: none;
            scrollbar-width: none;
        }
        
        .overflow-guard::-webkit-scrollbar {
            display: none;
        }
    </style>
</head>
<body>
    <!-- الهيدر -->
    <div class="header">
        <div class="header-line"></div>
    </div>
    
    <!-- المحتوى الرئيسي -->
    <div class="main-area">
        <div class="text-container">
            <div class="overflow-guard">
                <div class="text-content">{{ text }}</div>
            </div>
        </div>
    </div>
    
    <!-- الفوتر -->
    <div class="footer">
        <div class="footer-divider"></div>
        <div class="channel-name">{{ channel_name }}</div>
        <div class="channel-handle">{{ channel_handle }}</div>
    </div>
</body>
</html>"""
        
        template_file = Path(self.template_dir) / "card.html"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info("🎨 تم إنشاء قالب ثابت الأبعاد")

    async def render(self, text: str, message_id: int) -> str:
        """تصميم بطاقة ثابتة الأبعاد"""
        logger.info(f"🎨 جاري تصميم البطاقة #{message_id}")
        
        # تنظيف النص
        cleaned_text = text.strip()
        
        # معادلة ذكية لحجم الخط تحافظ على التنسيق
        text_length = len(cleaned_text)
        line_count = cleaned_text.count('\n') + 1
        
        if text_length < 50:
            font_size = 75
        elif text_length < 150:
            font_size = 65
        elif text_length < 300:
            font_size = 55
        elif text_length < 500:
            font_size = 48
        else:
            # للنصوص الطويلة، نحسب بناءً على عدد الأسطر
            if line_count > 15:
                font_size = 40
            else:
                font_size = 44
        
        # تحميل القالب
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        
        html_out = template.render(
            text=cleaned_text,
            font_size=font_size,
            channel_name=settings.CHANNEL_NAME,
            channel_handle=settings.CHANNEL_HANDLE
        )
        
        # مسار الملف الناتج
        output_path = Path(self.output_dir) / f"card_{message_id}.jpg"
        
        try:
            async with async_playwright() as p:
                # إعداد المتصفح
                browser = await p.chromium.launch(
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-setuid-sandbox'
                    ]
                )
                
                # إنشاء الصفحة بأبعاد ثابتة
                page = await browser.new_page(
                    viewport={
                        'width': self.WIDTH,
                        'height': self.HEIGHT
                    }
                )
                
                # تعيين المحتوى
                await page.set_content(html_out)
                
                # انتظار تحميل الخطوط والصور
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(300)  # وقت إضافي للتأكد
                
                # التقاط الشاشة
                await page.screenshot(
                    path=str(output_path),
                    type='jpeg',
                    quality=95,
                    full_page=False  # مهم: لا نستخدم full_page
                )
                
                await browser.close()
            
            # التحقق من حجم الصورة
            if output_path.exists():
                file_size = output_path.stat().st_size / 1024  # بالكيلوبايت
                logger.info(f"✅ تم إنشاء: {output_path} ({file_size:.1f} KB)")
            else:
                logger.error("❌ فشل إنشاء الملف")
                raise FileNotFoundError("فشل إنشاء الصورة")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ خطأ في التصميم: {e}")
            raise

    def validate_output(self, image_path: str) -> bool:
        """التحقق من جودة الصورة الناتجة"""
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            # التحقق من الأبعاد
            if img.size != (1080, 1350):
                logger.warning(f"❌ أبعاد غير صحيحة: {img.size}")
                return False
            
            # التحقق من أن الصورة ليست فارغة
            if img.getextrema() == ((0, 0), (0, 0), (0, 0)):
                logger.warning("❌ الصورة فارغة")
                return False
            
            return True
            
        except ImportError:
            logger.warning("⚠️ Pillow غير مثبت، تخطي التحقق")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق: {e}")
            return False

    def get_sample_text(self) -> str:
        """نص تجريبي للاختبار"""
        return """يا من ينامون على وسادة الأمل
ويحلمون بغدٍ أجمل

الليل يمر والنجوم تتلألأ
والصباح آتٍ لا محالة

لكل غيمةٍ شمسٌ تنتظرها
ولكل حزنٍ فرحةٌ تقترب"""


# استخدام للاختبار
async def test_generator():
    """دالة اختبار للمولد"""
    generator = ImageGenerator()
    
    # نص اختبار
    test_text = generator.get_sample_text()
    
    # توليد الصورة
    try:
        output = await generator.render(test_text, 999)
        print(f"✅ تم إنشاء: {output}")
        
        # التحقق
        if generator.validate_output(output):
            print("✅ الصورة صالحة")
        else:
            print("⚠️ هناك مشكلة في الصورة")
            
    except Exception as e:
        print(f"❌ فشل: {e}")

if __name__ == "__main__":
    asyncio.run(test_generator())