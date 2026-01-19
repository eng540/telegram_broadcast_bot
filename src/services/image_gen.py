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

# روابط الخطوط (نحتاج الوزنين: العادي للتذييل، والعريض للنص الشعري)
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
        تصميم HTML/CSS بناءً على وثيقة Elegant Minimalist V2
        """
        html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <style>
        /* تعريف الخطوط */
        @font-face { font-family: 'Amiri'; src: url('file:///app/assets/amiri_regular.ttf'); font-weight: 400; }
        @font-face { font-family: 'Amiri'; src: url('file:///app/assets/amiri_bold.ttf'); font-weight: 700; }
        
        body {
            margin: 0;
            /* الإطار الداخلي (Passe-partout) */
            padding: 100px; 
            width: 1080px;
            min-height: 1350px;
            
            /* لون الخلفية الأساسي: أوف وايت كريمي */
            background-color: #FDFBF7;
            
            font-family: 'Amiri', serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            
            /* اللون الرئيسي للنص: بني محروق جداً */
            color: #2C1E18;
            
            box-sizing: border-box;
        }

        /* منطقة النص الرئيسي */
        .main-content {
            width: 100%;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: center; /* توسيط عمودي */
            align-items: center;     /* توسيط أفقي */
            text-align: center;
        }

        .text-body {
            font-size: {{ font_size }}px;
            font-weight: 700; /* خط عريض للنص الشعري */
            line-height: 2.0; /* مسافة مريحة */
            white-space: pre-wrap;
        }

        /* منطقة التذييل */
        .footer-container {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            /* مسافة أمان سفلية إضافية لضمان عدم الالتصاق بالحافة */
            padding-bottom: 20px; 
            flex-shrink: 0;
        }

        /* الفاصل الزخرفي */
        .divider {
            width: 60%; /* ليس بعرض الصفحة كاملة لزيادة الأناقة */
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 25px;
        }

        .line {
            height: 1px;
            background-color: #BCAAA4; /* بني فاتح رمادي */
            flex-grow: 1;
        }

        .ornament {
            padding: 0 20px;
            color: #BCAAA4;
            font-size: 24px;
            line-height: 0; /* لضبط المحاذاة مع الخط */
        }

        /* اسم القناة */
        .brand-name {
            font-family: 'Amiri', serif;
            font-size: 32px;
            font-weight: 700; /* Bold */
            color: #2C1E18;
            margin-bottom: 15px;
            letter-spacing: 0.5px;
        }

        /* المعرف الاجتماعي (التصميم الجديد النظيف) */
        .handle-box {
            display: flex;
            align-items: center;
            justify-content: center;
            /* إزالة الخلفية والحدود (No Bubble) */
            background: transparent;
            border: none;
        }

        .telegram-icon {
            width: 22px;
            height: 22px;
            margin-left: 8px;
            fill: #C1A360; /* لون ذهبي مطفي */
        }

        .handle-text {
            font-family: 'Helvetica', 'Arial', sans-serif; /* خط إنجليزي نظيف */
            font-size: 22px;
            color: #C1A360; /* نفس لون الأيقونة */
            font-weight: 400;
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
        <!-- الفاصل -->
        <div class="divider">
            <div class="line"></div>
            <div class="ornament">✦</div>
            <div class="line"></div>
        </div>
        
        <!-- الاسم -->
        <div class="brand-name">{{ channel_name }}</div>
        
        <!-- المعرف -->
        <div class="handle-box">
            <!-- أيقونة تيليجرام -->
            <svg class="telegram-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .24z"/>
            </svg>
            <span class="handle-text">{{ channel_handle }}</span>
        </div>
    </div>
</body>
</html>"""
        
        with open(self.template_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering V2 Design: {message_id}")
        
        cleaned_text = text.strip()
        text_len = len(cleaned_text)
        
        # المنطق الديناميكي لحجم الخط (حسب الوثيقة)
        if text_len < 60:
            font_size = 110
        elif text_len < 150:
            font_size = 90
        elif text_len < 350:
            font_size = 75
        else:
            font_size = 60

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
                # استخدام دقة عالية
                page = await browser.new_page(viewport={'width': 1080, 'height': 1350}, device_scale_factor=2)
                
                await page.set_content(html_out)
                await page.wait_for_timeout(100)
                
                # التقاط الصورة (full_page=True لضمان عدم قص النصوص الطويلة جداً)
                await page.screenshot(path=str(output_path), type='jpeg', quality=98, full_page=True)
                await browser.close()
                
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Rendering Failed: {e}")
            raise