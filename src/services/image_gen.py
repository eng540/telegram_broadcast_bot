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
            "https://images.unsplash.com/photo-1507842217121-9e9f147d7121?q=80&w=1080",
            "https://images.unsplash.com/photo-1604076913837-52ab5629fba9?q=80&w=1080",
            "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1080"
        ]

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
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
                    background-color: #1a1a1a;
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
                    padding: 80px 60px;
                    background: rgba(0, 0, 0, 0.55);
                    backdrop-filter: blur(15px);
                    -webkit-backdrop-filter: blur(15px);
                    border-radius: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    box-shadow: 0 30px 60px rgba(0,0,0,0.7);
                    text-align: center;
                    color: #fff;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    min-height: 400px;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.8;
                    text-shadow: 0 2px 10px rgba(0,0,0,0.8);
                    white-space: pre-wrap;
                    margin-bottom: 60px;
                }

                .footer {
                    border-top: 1px solid rgba(255,255,255,0.3);
                    padding-top: 25px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 5px;
                }

                .channel-name {
                    font-family: 'Amiri', serif;
                    font-size: 28px;
                    color: #f0f0f0;
                    font-weight: 400;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 24px;
                    color: #ffd700; /* ذهبي */
                    letter-spacing: 2px;
                    direction: ltr;
                    font-weight: 700;
                }
            </style>
        </head>
        <body>
            <div class="glass-container">
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

    async def render(self, text: str, message_id: int, bg_path: str = None) -> str:
        if bg_path:
            bg_url = f"file://{bg_path}"
        else:
            bg_url = random.choice(self.fallback_backgrounds)

        text_len = len(text)
        if text_len < 50: font_size = 85
        elif text_len < 150: font_size = 70
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
            await page.wait_for_timeout(1500)
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path