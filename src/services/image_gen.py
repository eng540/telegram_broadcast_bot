import os
import logging
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

    def _create_template(self):
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
                    height: 1440px; /* نسبة 3:4 */
                    font-family: 'Amiri', serif;
                    background-color: #000;
                    background-image: url('{{ bg_url }}');
                    background-size: cover;
                    background-position: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }

                .glass-container {
                    width: 850px;
                    padding: 60px;
                    background: rgba(0, 0, 0, 0.4); /* خلفية داكنة شفافة */
                    backdrop-filter: blur(8px);
                    border-radius: 30px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
                    text-align: center;
                    color: #fff;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.7;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
                    white-space: pre-wrap;
                    margin-bottom: 40px;
                }

                .footer {
                    margin-top: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    opacity: 0.9;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 24px;
                    color: #ffd700; /* لون ذهبي */
                    letter-spacing: 1px;
                    direction: ltr;
                }
            </style>
        </head>
        <body>
            <div class="glass-container">
                <div class="text-body">{{ text }}</div>
                <div class="footer">
                    <span class="handle">""" + settings.CHANNEL_HANDLE + """</span>
                </div>
            </div>
        </body>
        </html>
        """
        with open(os.path.join(self.template_dir, "card.html"), "w") as f:
            f.write(html_content)

    async def render(self, text: str, message_id: int, bg_url: str = None) -> str:
        # خلفية احتياطية إذا فشل الذكاء الاصطناعي
        if not bg_url:
            bg_url = "https://images.unsplash.com/photo-1507842217121-9e9f147d7121"

        text_len = len(text)
        if text_len < 50: font_size = 80
        elif text_len < 150: font_size = 65
        elif text_len < 300: font_size = 55
        else: font_size = 45

        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        html_out = template.render(text=text, font_size=font_size, bg_url=bg_url)
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            await page.set_content(html_out)
            await page.wait_for_timeout(2000) # انتظار تحميل الخلفية
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path