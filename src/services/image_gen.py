import os
import logging
import random
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
        
        self.fallback_gradients = [
            "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
            "linear-gradient(135deg, #3a1c71 0%, #d76d77 50%, #ffaf7b 100%)",
            "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
            "linear-gradient(135deg, #141E30 0%, #243B55 100%)"
        ]

    def _calculate_font_size(self, text: str) -> int:
        """حساب ذكي لحجم الخط بناءً على الطول والأسطر"""
        length = len(text)
        lines = text.count('\n') + 1
        
        # معادلة الأمان: كلما زادت الأسطر، صغر الخط إجبارياً
        if lines > 10 or length > 400: return 40
        if lines > 8 or length > 300: return 50
        if lines > 6 or length > 200: return 60
        if lines > 4 or length > 100: return 75
        if length < 50: return 95 # نصوص قصيرة جداً
        return 80

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Reem+Kufi:wght@500;700&display=swap');
                
                * { box-sizing: border-box; }

                body {
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    height: 1440px;
                    font-family: 'Amiri', serif;
                    background-color: #000;
                    background: {{ bg_css }};
                    background-size: cover;
                    background-position: center;
                    overflow: hidden; /* منع الخروج عن الإطار */
                    
                    /* مركزية مطلقة */
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .cinematic-overlay {
                    position: absolute;
                    top: 0; left: 0; width: 100%; height: 100%;
                    background: radial-gradient(circle, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.6) 80%, rgba(0,0,0,0.9) 100%);
                    z-index: 1;
                }

                .safe-zone {
                    position: relative;
                    z-index: 2;
                    width: 900px;  /* عرض ثابت آمن */
                    height: 1200px; /* ارتفاع ثابت آمن */
                    display: flex;
                    flex-direction: column;
                    justify-content: center; /* توسيط عمودي */
                    align-items: center;
                    text-align: center;
                    /* حدود وهمية لضمان عدم الالتصاق بالحواف */
                    padding: 20px; 
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.7;
                    color: #ffffff;
                    text-shadow: 0 4px 15px rgba(0,0,0,1);
                    white-space: pre-wrap;
                    
                    /* في حال كان النص طويلاً جداً، لا يخرج بل يظهر نقاط (أمان إضافي) */
                    max-height: 1000px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                .footer {
                    margin-top: 60px; /* مسافة ثابتة عن النص */
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                    opacity: 0.9;
                }

                .channel-name {
                    font-family: 'Amiri', serif;
                    font-size: 30px;
                    color: #e0e0e0;
                    text-shadow: 0 2px 5px rgba(0,0,0,1);
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 26px;
                    color: #ffd700;
                    letter-spacing: 2px;
                    direction: ltr;
                    font-weight: 700;
                    text-shadow: 0 2px 5px rgba(0,0,0,1);
                }
            </style>
        </head>
        <body>
            <div class="cinematic-overlay"></div>
            
            <div class="safe-zone">
                <div class="text-body">{{ text }}</div>
                
                <div class="footer">
                    <div class="channel-name">""" + settings.CHANNEL_NAME + """</div>
                    <div class="handle">""" + settings.CHANNEL_HANDLE + """</div>
                </div>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int, bg_data: str = None) -> str:
        if bg_data and bg_data.startswith("data:image"):
            bg_css = f"url('{bg_data}')"
        else:
            bg_css = random.choice(self.fallback_gradients)

        # استخدام المعادلة الذكية
        font_size = self._calculate_font_size(text)

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        
        html_out = template.render(
            text=text, 
            font_size=font_size, 
            bg_css=bg_css
        )
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            await page.set_content(html_out)
            await page.wait_for_timeout(1000)
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path