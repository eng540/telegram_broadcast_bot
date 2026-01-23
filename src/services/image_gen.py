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
        
        # خلفيات طوارئ مجانية
        self.fallback_backgrounds = [
            "https://images.unsplash.com/photo-1542259681-d2b3c921d71e?q=80&w=1080",
            "https://images.unsplash.com/photo-1518066000714-58c45f1a2c0a?q=80&w=1080",
            "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1080"
        ]

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
        # تصميم فخم ومندمج
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
                    background-image: url('{{ bg_url }}');
                    background-size: cover;
                    background-position: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    /* ✅ خطوة إضافية: تهدئة الخلفية لو كانت صاخبة */
                    position: relative;
                }
                /* ✅ طبقة تصفية خفيفة على الخلفية فقط */
                body::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(15, 23, 42, 0.25); /* لون أزرق داكن شفاف */
                    z-index: 1;
                }

                .glass-card {
                    width: 850px;
                    padding: 70px 50px;
                    /* ✅ الحل الأساسي: تأثير زجاجي فاتح وشفاف */
                    background: rgba(255, 255, 255, 0.08); /* أبيض شفاف بدلاً من أسود */
                    backdrop-filter: blur(25px) saturate(1.6); /* زيادة قوة البلور */
                    -webkit-backdrop-filter: blur(25px) saturate(1.6);
                    border-radius: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.25); /* حدود أكثر وضوحاً للتعريف */
                    box-shadow: 
                        0 30px 60px rgba(0, 0, 0, 0.6), /* ظل خارجي */
                        inset 0 1px 0 rgba(255, 255, 255, 0.2); /* إضاءة داخلية خفيفة */
                    text-align: center;
                    color: #fff;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    min-height: 500px;
                    position: relative; /* ✅ يجعل الكارد فوق طبعة body::before */
                    z-index: 2;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.8;
                    /* ✅ تحسين النص للوضوح على الخلفية الشفافة */
                    color: rgba(255, 255, 255, 0.98);
                    text-shadow: 
                        0 2px 4px rgba(0, 0, 0, 0.5),
                        0 0 30px rgba(255, 215, 0, 0.15); /* وهج ذهبي خفيف */
                    white-space: pre-wrap;
                    margin-bottom: 50px;
                }

                .footer {
                    border-top: 1px solid rgba(255, 255, 255, 0.15); /* خط فاتح أكثر */
                    padding-top: 20px;
                    margin-top: auto;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 26px;
                    color: #ffd700;
                    letter-spacing: 2px;
                    direction: ltr;
                    text-shadow: 0 0 10px rgba(255, 215, 0, 0.3); /* توهج للاسم */
                }
            </style>
        </head>
        <body>
            <div class="glass-card">
                <div class="text-body">{{ text }}</div>
                <div class="footer">
                    <div class="handle">""" + settings.CHANNEL_HANDLE + """</div>
                </div>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int, bg_url: str = None) -> str:
        if not bg_url:
            bg_url = random.choice(self.fallback_backgrounds)

        text_len = len(text)
        if text_len < 50: font_size = 90
        elif text_len < 150: font_size = 75
        elif text_len < 300: font_size = 60
        else: font_size = 50

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(text=text, font_size=font_size, bg_url=bg_url)
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            await page.set_content(html_out)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path