import os
import logging
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from src.config import settings

# إعداد السجلات
logger = logging.getLogger("HtmlRenderer")
logger.setLevel(logging.INFO)

# إصدار الخط الأنسب للأدب العربي
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"

class ImageGenerator:
    def __init__(self):
        """تهيئة مولد الصور"""
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        # استخدام Path للتعامل مع الملفات
        self.font_path = Path(self.assets_dir) / "amiri_regular.ttf"
        self.template_file = Path(self.template_dir) / "card.html"
        
        # إنشاء المجلدات إذا لم تكن موجودة
        for directory in [self.output_dir, self.assets_dir, self.template_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # تهيئة المكونات
        self._ensure_font()
        self._create_template()

    def _ensure_font(self):
        """التأكد من وجود الخط وتحميله إذا لزم الأمر"""
        # حذف الخط القديم إذا كان عريضاً
        old_bold_font = Path(self.assets_dir) / "amiri_bold.ttf"
        if old_bold_font.exists():
            try:
                old_bold_font.unlink()
                logger.info("🗑️ حذف الخط العريض القديم")
            except Exception as e:
                logger.warning(f"تعذر حذف الخط القديم: {e}")
        
        # تحميل الخط إذا كان غير موجود أو صغير الحجم
        if not self.font_path.exists() or self.font_path.stat().st_size < 10000:
            try:
                logger.info("⬇️ جاري تحميل خط Amiri-Regular...")
                urllib.request.urlretrieve(FONT_URL, str(self.font_path))
                logger.info(f"✅ تم تحميل الخط: {self.font_path}")
            except Exception as e:
                logger.error(f"❌ فشل تحميل الخط: {e}")
                # استخدام خط بديل إذا لزم الأمر
                raise

    def _create_template(self):
        """إنشاء قالب HTML للبطاقة"""
        html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بطاقة أدبية</title>
    <style>
        /* تعريف الخط العربي الأنيق */
        @font-face {
            font-family: 'Amiri';
            src: url('file:///app/assets/amiri_regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        
        /* الأنماط الأساسية */
        body {
            margin: 0;
            padding: 0;
            width: 1080px;
            min-height: 1350px;
            background: linear-gradient(135deg, #fefefe 0%, #fafafa 100%);
            font-family: 'Amiri', serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            color: #2c1e18;
            box-sizing: border-box;
            position: relative;
            overflow: hidden;
        }
        
        /* خلفية زخرفية خفيفة */
        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: 
                radial-gradient(circle at 20% 80%, rgba(188, 170, 164, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(188, 170, 164, 0.05) 0%, transparent 50%);
            z-index: -1;
        }
        
        /* المحتوى الرئيسي */
        .main-content {
            width: 850px;
            padding: 150px 0 100px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }
        
        .text-body {
            font-size: {{ font_size }}px;
            font-weight: 400;
            line-height: 2.2;
            white-space: pre-wrap;
            word-wrap: break-word;
            hyphens: auto;
            text-shadow: 0.5px 0.5px 1px rgba(0, 0, 0, 0.1);
        }
        
        /* التذييل */
        .footer-container {
            width: 600px;
            margin-top: 50px;
            display: flex;
            flex-direction: column;
            align-items: center;
            flex-shrink: 0;
            padding-bottom: 40px;
        }
        
        .divider {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 25px;
            position: relative;
        }
        
        .line {
            height: 1px;
            background: linear-gradient(90deg, transparent, #bcaaa4, transparent);
            flex-grow: 1;
        }
        
        .ornament {
            padding: 0 20px;
            color: #8d6e63;
            font-size: 18px;
            background-color: #fefefe;
            z-index: 1;
        }
        
        .brand-name {
            font-family: 'Amiri', serif;
            font-size: 34px;
            font-weight: 700;
            color: #3e2723;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }
        
        .handle-box {
            display: flex;
            align-items: center;
            background: linear-gradient(135deg, #f8f8f8 0%, #f0f0f0 100%);
            padding: 10px 30px;
            border-radius: 50px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .handle-box:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .handle-text {
            font-size: 22px;
            color: #0088cc;
            font-weight: 600;
            font-family: system-ui, -apple-system, sans-serif;
            direction: ltr;
            letter-spacing: 0.5px;
        }
        
        /* تأثيرات تفاعلية للصورة */
        .text-body::selection {
            background-color: rgba(188, 170, 164, 0.3);
        }
    </style>
</head>
<body>
    <div class="main-content">
        <div class="text-body">{{ text }}</div>
    </div>
    
    <div class="footer-container">
        <div class="divider">
            <div class="line"></div>
            <div class="ornament">❁</div>
            <div class="line"></div>
        </div>
        <div class="brand-name">{{ channel_name }}</div>
        <div class="handle-box">
            <span class="handle-text">{{ channel_handle }}</span>
        </div>
    </div>
</body>
</html>"""
        
        # حفظ القالب
        with open(self.template_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ تم إنشاء القالب: {self.template_file}")

    async def render(self, text: str, message_id: int) -> str:
        """تصميم البطاقة بناءً على النص المدخل"""
        logger.info(f"🎨 جاري تصميم البطاقة #{message_id}")
        
        # تنظيف النص
        cleaned_text = text.strip().replace('\r\n', '\n').replace('\r', '\n')
        
        # تحديد حجم الخط حسب طول النص
        text_len = len(cleaned_text)
        if text_len < 50:
            font_size = 100  # كبير للنصوص القصيرة جداً
        elif text_len < 120:
            font_size = 85   # متوسط للنصوص القصيرة
        elif text_len < 250:
            font_size = 70   # مناسب للنصوص المتوسطة
        elif text_len < 350:
            font_size = 60   # مناسب للنصوص الطويلة
        else:
            font_size = 52   # صغير للنصوص الطويلة جداً
        
        # تحميل القالب وتعبئته
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        
        html_out = template.render(
            text=cleaned_text,
            font_size=font_size,
            channel_name=settings.CHANNEL_NAME,
            channel_handle=settings.CHANNEL_HANDLE
        )
        
        # مسار الإخراج
        output_path = Path(self.output_dir) / f"card_{message_id}_{hash(cleaned_text[:50])}.jpg"
        
        try:
            # استخدام Playwright لالتقاط الصورة
            async with async_playwright() as p:
                # تشغيل المتصفح
                browser = await p.chromium.launch(
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-software-rasterizer'
                    ]
                )
                
                # إنشاء صفحة جديدة
                page = await browser.new_page(
                    viewport={'width': 1080, 'height': 1350},
                    device_scale_factor=2  # دقة أعلى للصور
                )
                
                # تعيين المحتوى وانتظار التحميل
                await page.set_content(html_out)
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(200)  # انتظار إضافي للتأكد من التحميل
                
                # التقاط الصورة
                await page.screenshot(
                    path=str(output_path),
                    type='jpeg',
                    quality=98,  # جودة عالية
                    full_page=True
                )
                
                # إغلاق المتصفح
                await browser.close()
            
            logger.info(f"✅ تم إنشاء البطاقة: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ فشل في تصميم البطاقة: {e}")
            raise

    def cleanup_old_files(self, max_age_hours: int = 24):
        """تنظيف الملفات القديمة"""
        import time
        from datetime import datetime, timedelta
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        for file_path in Path(self.output_dir).glob("card_*.jpg"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"🗑️ تم حذف الملف القديم: {file_path.name}")
            except Exception as e:
                logger.warning(f"تعذر حذف {file_path}: {e}")