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
        
        self.fallback_backgrounds = [
            "https://images.unsplash.com/photo-1542259681-d2b3c921d71e?q=80&w=1080",
            "https://images.unsplash.com/photo-1518066000714-58c45f1a2c0a?q=80&w=1080",
            "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1080"
        ]

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
        # تصميم "السينما" (بدون صندوق)
        html_content = """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Reem+Kufi:wght@500;700&display=swap');
                
                body {
                    margin: 0;
                    padding: 0;
                    width: 1080px;
                    height: 1440px;
                    font-family: 'Amiri', serif;
                    background-color: #000;
                    
                    /* الصورة الخلفية */
                    background-image: url('{{ bg_url }}');
                    background-size: cover;
                    background-position: center;
                    
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    position: relative;
                }

                /* طبقة التعتيم الذكية: تدرج لوني يغطي الصورة بالكامل */
                /* يجعل الصورة داكنة قليلاً لتبرز الكتابة البيضاء والذهبية */
                .overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(
                        to bottom,
                        rgba(0, 0, 0, 0.3) 0%,
                        rgba(0, 0, 0, 0.6) 50%,
                        rgba(0, 0, 0, 0.8) 100%
                    );
                    z-index: 1;
                }

                /* المحتوى يطفو فوق الطبقة */
                .content-wrapper {
                    position: relative;
                    z-index: 2;
                    width: 80%;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 40px;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.9;
                    color: #ffffff;
                    /* ظل خفيف للنص لضمان القراءة فوق أي خلفية */
                    text-shadow: 0 4px 10px rgba(0,0,0,0.8);
                    white-space: pre-wrap;
                }

                .divider {
                    width: 100px;
                    height: 3px;
                    background-color: #ffd700; /* خط ذهبي فاصل */
                    border-radius: 2px;
                    box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
                }

                .footer {
                    margin-top: 20px;
                    opacity: 0.9;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 28px;
                    color: #ffd700;
                    letter-spacing: 2px;
                    direction: ltr;
                    text-shadow: 0 2px 5px rgba(0,0,0,1);
                }
            </style>
        </head>
        <body>
            <div class="overlay"></div>
            
            <div class="content-wrapper">
                <div class="text-body">{{ text }}</div>
                <div class="divider"></div>
                <div class="footer">
                    <div class="handle">""" + settings.CHANNEL_HANDLE + """</div>
                </div>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int, bg_path: str = None) -> str:
        if bg_path:
            bg_url = f"file://{bg_path}"
        else:
            bg_url = random.choice(self.fallback_backgrounds)

        # تكبير الخط قليلاً لأننا أزلنا الصندوق
        text_len = len(text)
        if text_len < 50: font_size = 100
        elif text_len < 150: font_size = 80
        elif text_len < 300: font_size = 65
        else: font_size = 55

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(text=text, font_size=font_size, bg_url=bg_url)
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            await page.set_content(html_out)
            await page.wait_for_timeout(1500)
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path