"""
===========================================================
 Modern HTML/CSS Rendering Engine (Playwright)
 The Professional Standard
===========================================================
"""
import os
import logging
import asyncio
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("HtmlRenderer")
logging.basicConfig(level=logging.INFO)

class ImageGenerator:
    def __init__(self):
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        # إنشاء قالب HTML احترافي (مدمج هنا للسرعة، ويمكن فصله)
        self._create_template()
        
        os.makedirs(self.output_dir, exist_ok=True)

    def _create_template(self):
        """إنشاء ملف HTML/CSS الذي يمثل التصميم"""
        os.makedirs(self.template_dir, exist_ok=True)
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap');
                
                body {
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    height: 1350px;
                    background: url('file:///app/assets/template.jpg') no-repeat center center;
                    background-size: cover;
                    font-family: 'Amiri', serif;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                    color: #3e2723; /* بني داكن */
                }

                .content-box {
                    width: 700px; /* العرض الآمن */
                    min-height: 400px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    /* تأثيرات سينمائية */
                    text-shadow: 0px 2px 4px rgba(0,0,0,0.1); 
                }

                .text-content {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.8;
                    white-space: pre-wrap; /* احترام الأسطر */
                }

                .footer {
                    position: absolute;
                    bottom: 180px;
                    font-size: 35px;
                    opacity: 0.8;
                    font-weight: 400;
                }
            </style>
        </head>
        <body>
            <div class="content-box">
                <div class="text-content">{{ text }}</div>
            </div>
            <div class="footer">روائع الأدب العربي</div>
        </body>
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering via Browser Engine: {message_id}")
        
        # تحديد حجم الخط ديناميكياً (CSS Logic)
        text_len = len(text)
        if text_len < 50: font_size = 90
        elif text_len < 100: font_size = 75
        elif text_len < 200: font_size = 60
        else: font_size = 50

        # تجهيز HTML
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(text=text, font_size=font_size)
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        # تشغيل المتصفح والتقاط الصورة
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1350})
            
            await page.set_content(html_out)
            # انتظار تحميل الخطوط والصورة
            await page.wait_for_timeout(100) 
            
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path