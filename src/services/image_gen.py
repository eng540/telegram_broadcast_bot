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
            "linear-gradient(135deg, #134e5e 0%, #71b280 100%)",
            "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
            "linear-gradient(135deg, #4b6cb7 0%, #182848 100%)",
            "linear-gradient(135deg, #232526 0%, #414345 100%)"
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
                    
                    /* الخلفية: إما صورة Base64 أو تدرج */
                    background: {{ bg_css }};
                    background-size: cover;
                    background-position: center;
                    
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }

                /* طبقة تعتيم مدمجة */
                .overlay {
                    position: absolute;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0, 0, 0, 0.4);
                    z-index: 0;
                }

                .glass-container {
                    position: relative;
                    z-index: 1;
                    width: 850px;
                    padding: 80px 60px;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border-radius: 50px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 30px 60px rgba(0,0,0,0.5);
                    text-align: center;
                    color: #fff;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.8;
                    text-shadow: 0 4px 10px rgba(0,0,0,0.6);
                    white-space: pre-wrap;
                    margin-bottom: 50px;
                }

                .footer {
                    border-top: 1px solid rgba(255,255,255,0.3);
                    padding-top: 25px;
                    width: 80%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 26px;
                    color: #ffd700;
                    letter-spacing: 2px;
                    direction: ltr;
                }
            </style>
        </head>
        <body>
            <div class="overlay"></div>
            <div class="glass-container">
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

    async def render(self, text: str, message_id: int, bg_data: str = None) -> str:
        # إذا وصلتنا بيانات Base64، نستخدمها كـ URL
        if bg_data and bg_data.startswith("data:image"):
            bg_css = f"url('{bg_data}')"
            logger.info("🖼️ Rendering with AI Background (Base64)")
        else:
            # وإلا نستخدم التدرج
            bg_css = random.choice(self.fallback_gradients)
            logger.info("🎨 Rendering with Fallback Gradient")

        text_len = len(text)
        if text_len < 50: font_size = 95
        elif text_len < 150: font_size = 75
        elif text_len < 300: font_size = 60
        else: font_size = 50

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