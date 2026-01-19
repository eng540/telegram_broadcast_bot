import os
import logging
import urllib.request
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from src.config import settings

logger = logging.getLogger("HtmlRenderer")
logging.basicConfig(level=logging.INFO)

# 👇 التغيير 1: عدنا لنسخة Regular لأنها أجمل وأرق في الشعر
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"

class ImageGenerator:
    def __init__(self):
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        # سنسمي الملف amiri_regular ليكون واضحاً
        self.font_path = os.path.join(self.assets_dir, "amiri_regular.ttf")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        
        self._ensure_font()
        self._create_template()

    def _ensure_font(self):
        # نحذف الخط القديم إذا كان موجوداً لضمان تحميل النسخة الجديدة
        if os.path.exists(self.font_path) and "bold" in self.font_path:
             os.remove(self.font_path)

        if not os.path.exists(self.font_path) or os.path.getsize(self.font_path) < 10000:
            try:
                logger.info("⬇️ Downloading Amiri-Regular Font...")
                urllib.request.urlretrieve(FONT_URL, self.font_path)
            except Exception as e:
                logger.error(f"Font Download Error: {e}")

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                /* تعريف الخط */
                @font-face { 
                    font-family: 'Amiri'; 
                    src: url('file:///app/assets/amiri_regular.ttf'); 
                }
                
                body {
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    min-height: 1350px;
                    background-color: #ffffff;
                    font-family: 'Amiri', serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: space-between;
                    color: #2c1e18; /* بني داكن كلاسيكي */
                    box-sizing: border-box;
                    padding-bottom: 50px;
                }

                .main-content {
                    width: 850px;
                    padding-top: 150px;
                    padding-bottom: 100px;
                    flex-grow: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    /* 👇 التغيير 2: الوزن 400 (عادي) بدلاً من 700 (عريض) */
                    font-weight: 400; 
                    line-height: 2.0; /* زيادة التباعد قليلاً للأناقة */
                    text-align: center;
                    white-space: pre-wrap;
                }

                .footer-container {
                    width: 600px;
                    margin-top: 50px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    opacity: 0.9;
                    flex-shrink: 0;
                }

                .divider {
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 25px;
                }

                .line {
                    height: 1px; /* خط أنحف */
                    background-color: #bcaaa4;
                    flex-grow: 1;
                }

                .ornament {
                    padding: 0 15px;
                    color: #8d6e63;
                    font-size: 20px;
                }

                .brand-name {
                    font-family: 'Amiri', serif;
                    font-size: 36px;
                    font-weight: 700; /* الاسم يبقى عريضاً للتميز */
                    color: #3e2723;
                    margin-bottom: 10px;
                }

                .handle-box {
                    display: flex;
                    align-items: center;
                    background-color: #f5f5f5;
                    padding: 8px 25px;
                    border-radius: 50px;
                    border: 1px solid #e0e0e0;
                }

                .handle-text {
                    font-size: 22px;
                    color: #0088cc;
                    font-weight: 600;
                    font-family: sans-serif;
                    margin-left: 10px;
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
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering Elegant Card: {message_id}")
        
        text_len = len(text)
        # تعديل الأحجام لتناسب الخط العادي (Regular)
        if text_len < 50: font_size = 95
        elif text_len < 150: font_size = 80
        elif text_len < 300: font_size = 65
        else: font_size = 55

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(
            text=text, 
            font_size=font_size,
            channel_name=settings.CHANNEL_NAME,
            channel_handle=settings.CHANNEL_HANDLE
        )
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1350})
            
            await page.set_content(html_out)
            await page.wait_for_timeout(100)
            
            await page.screenshot(path=output_path, type='jpeg', quality=95, full_page=True)
            await browser.close()
            
        return output_path