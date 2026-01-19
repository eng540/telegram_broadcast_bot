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

# نستخدم النسخة العادية (Regular) لأنها أجمل في الشعر، والنسخة العريضة (Bold) للعناوين
FONT_REGULAR_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
FONT_BOLD_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"

class ImageGenerator:
    def __init__(self):
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        self.font_reg_path = Path(self.assets_dir) / "amiri_regular.ttf"
        self.font_bold_path = Path(self.assets_dir) / "amiri_bold.ttf"
        self.template_file = Path(self.template_dir) / "card.html"
        
        # إنشاء المجلدات
        for directory in [self.output_dir, self.assets_dir, self.template_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self._ensure_fonts()
        self._create_template()

    def _ensure_fonts(self):
        """تحميل الخطوط المطلوبة"""
        fonts = [
            (self.font_reg_path, FONT_REGULAR_URL),
            (self.font_bold_path, FONT_BOLD_URL)
        ]
        
        for path, url in fonts:
            if not path.exists() or path.stat().st_size < 10000:
                try:
                    logger.info(f"⬇️ جاري تحميل الخط: {path.name}...")
                    urllib.request.urlretrieve(url, str(path))
                except Exception as e:
                    logger.error(f"❌ فشل تحميل الخط {path.name}: {e}")

    def _create_template(self):
        """
        تصميم HTML/CSS بمواصفات عالمية (Typography Best Practices)
        """
        html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <style>
        /* تعريف الخطوط */
        @font-face { font-family: 'Amiri'; src: url('file:///app/assets/amiri_regular.ttf'); font-weight: normal; }
        @font-face { font-family: 'Amiri-Bold'; src: url('file:///app/assets/amiri_bold.ttf'); font-weight: bold; }
        
        body {
            margin: 0;
            padding: 0;
            width: 1080px;
            /* الطول يتمدد حسب المحتوى */
            min-height: 1350px; 
            
            /* خلفية لؤلؤية فاخرة (Off-White Gradient) */
            background: linear-gradient(180deg, #ffffff 0%, #fcfcfc 100%);
            
            font-family: 'Amiri', serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            color: #1a1a1a; /* أسود فحمي (ليس أسود كامل) لراحة العين */
            box-sizing: border-box;
            padding-bottom: 60px;
        }

        /* منطقة النص الرئيسية */
        .main-content {
            width: 800px; /* عرض مريح للقراءة */
            padding-top: 180px;
            padding-bottom: 100px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }

        .text-body {
            font-size: {{ font_size }}px;
            font-weight: normal; /* خط عادي للأناقة */
            line-height: 2.3;    /* تباعد أسطر واسع (فخامة) */
            white-space: pre-wrap;
            
            /* ظل خفيف جداً للنص لزيادة الوضوح */
            text-shadow: 0px 1px 1px rgba(0,0,0,0.05);
        }

        /* منطقة التذييل */
        .footer-container {
            width: 500px;
            margin-top: 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
            opacity: 0.85;
            flex-shrink: 0;
        }

        .divider {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }

        .line {
            height: 1px;
            background-color: #d1d1d1; /* خط رمادي فاتح */
            flex-grow: 1;
        }

        .ornament {
            padding: 0 20px;
            color: #8d6e63; /* لون بني نحاسي */
            font-size: 22px;
            font-family: serif;
        }

        .brand-name {
            font-family: 'Amiri-Bold', serif; /* اسم القناة بالخط العريض */
            font-size: 32px;
            color: #3e2723;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }

        .handle-box {
            background-color: #f7f7f7;
            padding: 6px 25px;
            border-radius: 50px;
            border: 1px solid #eeeeee;
            display: flex;
            align-items: center;
        }

        .handle-text {
            font-size: 20px;
            color: #0088cc; /* لون تيليجرام */
            font-weight: 600;
            font-family: sans-serif;
            direction: ltr;
            letter-spacing: 1px;
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
            <div class="ornament">✦</div>
            <div class="line"></div>
        </div>
        <div class="brand-name">{{ channel_name }}</div>
        <div class="handle-box">
            <span class="handle-text">{{ channel_handle }}</span>
        </div>
    </div>
</body>
</html>"""
        
        with open(self.template_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering Premium Card: {message_id}")
        
        # تنظيف النص
        cleaned_text = text.strip()
        text_len = len(cleaned_text)
        
        # معادلة حجم الخط (موزونة بدقة)
        if text_len < 40: font_size = 100    # عبارات قصيرة جداً
        elif text_len < 100: font_size = 80  # اقتباسات متوسطة
        elif text_len < 250: font_size = 65  # شعر متوسط
        elif text_len < 400: font_size = 55  # نصوص طويلة
        else: font_size = 48                 # نصوص طويلة جداً

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        
        html_out = template.render(
            text=cleaned_text,
            font_size=font_size,
            channel_name=settings.CHANNEL_NAME,
            channel_handle=settings.CHANNEL_HANDLE
        )
        
        output_path = Path(self.output_dir) / f"card_{message_id}.jpg"
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=['--no-sandbox'])
                # نستخدم device_scale_factor=2 للحصول على دقة Retina (عالية جداً)
                page = await browser.new_page(viewport={'width': 1080, 'height': 1350}, device_scale_factor=2)
                
                await page.set_content(html_out)
                await page.wait_for_timeout(100)
                
                # التقاط الصورة كاملة
                await page.screenshot(path=str(output_path), type='jpeg', quality=98, full_page=True)
                await browser.close()
                
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Rendering Failed: {e}")
            raise