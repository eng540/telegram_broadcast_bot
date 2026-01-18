"""
===========================================================
 Modern HTML/CSS Rendering Engine (Playwright)
 Dynamic Height Edition (Smart Scroll) 📜
===========================================================
"""
import os
import logging
import asyncio
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("HtmlRenderer")
logging.basicConfig(level=logging.INFO)

CHANNEL_NAME = "روائع الأدب العربي"
CHANNEL_HANDLE = "@Rwaea3"

class ImageGenerator:
    def __init__(self):
        self.output_dir = "/app/data"
        self.assets_dir = "/app/assets"
        self.template_dir = "/app/templates"
        
        self._create_template()
        os.makedirs(self.output_dir, exist_ok=True)

    def _create_template(self):
        """
        تصميم مرن (Flexbox) يسمح بالتمدد الرأسي
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
                    /* السر هنا: الحد الأدنى 1350، لكنه قابل للزيادة */
                    min-height: 1350px; 
                    background-color: #ffffff;
                    font-family: 'Amiri', serif;
                    
                    /* تحويل الجسم إلى عمود مرن */
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: space-between; /* يباعد بين المحتوى والتذييل */
                    
                    color: #2c1e18;
                    box-sizing: border-box; /* حساب الهوامش ضمن الطول */
                    padding-bottom: 50px; /* هامش سفلي أمان */
                }

                .main-content {
                    width: 850px; /* وسعنا العرض قليلاً */
                    padding-top: 120px;
                    padding-bottom: 80px;
                    
                    /* يسمح للمحتوى بالنمو ودفعه للأسفل */
                    flex-grow: 1; 
                    display: flex;
                    flex-direction: column;
                    justify-content: center; /* توسيط النص في المساحة المتاحة */
                    align-items: center;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.8;
                    text-align: center;
                    white-space: pre-wrap; /* يحترم الأسطر والمسافات */
                }

                .footer-container {
                    width: 600px;
                    margin-top: 50px; /* مسافة فاصلة عن النص */
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    opacity: 0.9;
                    /* نضمن أن التذييل لا يتقلص */
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
                    height: 2px;
                    background-color: #bcaaa4;
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
                    fill: #0088cc;
                }

                .handle-text {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 24px;
                    color: #0088cc;
                    font-weight: 600;
                    direction: ltr;
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
                <div class="brand-name">""" + CHANNEL_NAME + """</div>
                <div class="handle-box">
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
        logger.info(f"🎨 Rendering Dynamic Height: {message_id}")
        
        text_len = len(text)
        
        # معادلة ذكية لحجم الخط:
        # النصوص الطويلة جداً (مثل القصائد) تحتاج خطاً متوسطاً (ليس صغيراً جداً) لتبقى مقروءة
        if text_len < 50: font_size = 90
        elif text_len < 150: font_size = 70
        elif text_len < 300: font_size = 60
        else: font_size = 55  # القصائد الطويلة تثبت على حجم 55

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(text=text, font_size=font_size)
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
            # نفتح صفحة بعرض ثابت وطول افتراضي
            page = await browser.new_page(viewport={'width': 1080, 'height': 1350})
            
            await page.set_content(html_out)
            await page.wait_for_timeout(100)
            
            # --- السحر هنا ---
            # full_page=True: تخبر المتصفح أن يلتقط الصورة كاملة حتى لو كان هناك "سكرول"
            await page.screenshot(path=output_path, type='jpeg', quality=95, full_page=True)
            
            await browser.close()
            
        return output_path