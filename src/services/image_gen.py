"""
===========================================================
 Modern HTML/CSS Rendering Engine (Playwright)
 Professional Branding Edition 💎
===========================================================
"""
import os
import logging
import asyncio
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("HtmlRenderer")
logging.basicConfig(level=logging.INFO)

# إعدادات القناة (يمكنك تغييرها هنا بسهولة)
CHANNEL_NAME = "روائع الأدب العربي"
CHANNEL_HANDLE = "@Rwaea3"

class ImageGenerator:
    def __init__(self):
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        # إنشاء القالب الجديد
        self._create_template()
        
        os.makedirs(self.output_dir, exist_ok=True)

    def _create_template(self):
        """
        تصميم HTML/CSS احترافي مع تذييل 'الختم الملكي'
        """
        os.makedirs(self.template_dir, exist_ok=True)
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Reem+Kufi:wght@500&display=swap');
                
                body {
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    height: 1350px;
                    background-color: #ffffff; /* خلفية بيضاء نقية */
                    /* يمكنك تفعيل السطر التالي إذا أردت خلفية ورقية */
                    /* background: url('file:///app/assets/template.jpg') no-repeat center center; background-size: cover; */
                    
                    font-family: 'Amiri', serif;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between; /* توزيع المساحة بين المحتوى والتذييل */
                    align-items: center;
                    color: #2c1e18; /* لون بني داكن جداً للنص */
                }

                /* حاوية النص الرئيسي */
                .main-content {
                    flex-grow: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    width: 800px;
                    padding-top: 100px; /* مساحة من الأعلى */
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.9; /* تباعد أسطر مريح */
                    text-align: center;
                    white-space: pre-wrap;
                }

                /* تصميم التذييل (الختم الملكي) */
                .footer-container {
                    width: 600px;
                    padding-bottom: 80px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    opacity: 0.9;
                }

                .divider {
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 25px;
                }

                .line {
                    height: 2px;
                    background-color: #bcaaa4; /* لون ذهبي/بيج غامق */
                    flex-grow: 1;
                    border-radius: 2px;
                }

                .ornament {
                    padding: 0 15px;
                    color: #8d6e63;
                    font-size: 24px;
                }

                .brand-name {
                    font-family: 'Amiri', serif;
                    font-size: 38px;
                    font-weight: 700;
                    color: #3e2723;
                    margin-bottom: 10px;
                    letter-spacing: 1px;
                }

                .handle-box {
                    display: flex;
                    align-items: center;
                    background-color: #f5f5f5;
                    padding: 8px 25px;
                    border-radius: 50px;
                    border: 1px solid #e0e0e0;
                }

                .telegram-icon {
                    width: 24px;
                    height: 24px;
                    margin-left: 10px;
                    fill: #0088cc; /* لون تيليجرام الرسمي */
                }

                .handle-text {
                    font-family: 'Reem Kufi', sans-serif; /* خط عصري للمعرف */
                    font-size: 24px;
                    color: #0088cc;
                    font-weight: 600;
                    direction: ltr; /* المعرف يظهر باليسار */
                }

            </style>
        </head>
        <body>
            
            <!-- المحتوى النصي -->
            <div class="main-content">
                <div class="text-body">{{ text }}</div>
            </div>

            <!-- التذييل الاحترافي -->
            <div class="footer-container">
                <!-- الفاصل الزخرفي -->
                <div class="divider">
                    <div class="line"></div>
                    <div class="ornament">✦</div>
                    <div class="line"></div>
                </div>

                <!-- اسم القناة -->
                <div class="brand-name">""" + CHANNEL_NAME + """</div>

                <!-- المعرف مع الأيقونة -->
                <div class="handle-box">
                    <!-- أيقونة تيليجرام SVG -->
                    <svg class="telegram-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .24z"/>
                    </svg>
                    <span class="handle-text">""" + CHANNEL_HANDLE + """</span>
                </div>
            </div>

        </body>
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering Branding Card: {message_id}")
        
        text_len = len(text)
        # تكبير الخطوط قليلاً لأن الخلفية البيضاء تحتمل ذلك
        if text_len < 50: font_size = 100
        elif text_len < 100: font_size = 85
        elif text_len < 200: font_size = 65
        else: font_size = 55

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(text=text, font_size=font_size)
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1350})
            
            await page.set_content(html_out)
            await page.wait_for_timeout(100)
            
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path