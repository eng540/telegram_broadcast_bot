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
        
        # خلفيات تدرج لوني (للطوارئ فقط)
        self.fallback_gradients = [
            "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
            "linear-gradient(135deg, #141E30 0%, #243B55 100%)",
            "linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%)"
        ]

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
        # تصميم سينمائي (بدون صندوق محدد)
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
                    
                    /* الخلفية */
                    background: {{ bg_css }};
                    background-size: cover;
                    background-position: center;
                    
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    overflow: hidden;
                }

                /* الطبقة السحرية: تدرج لوني كامل لتعتيم الخلفية وإبراز النص */
                .cinematic-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    /* تدرج من الشفاف في الأعلى إلى الداكن في الأسفل والوسط */
                    background: radial-gradient(circle at center, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.8) 100%),
                                linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.6) 100%);
                    z-index: 1;
                }

                /* حاوية النص (شفافة تماماً) */
                .content-wrapper {
                    position: relative;
                    z-index: 2;
                    width: 85%;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 50px;
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.9;
                    color: #ffffff;
                    /* ظل قوي وحاد للنص لضمان القراءة فوق أي لون */
                    text-shadow: 0 5px 15px rgba(0,0,0,0.9), 0 2px 4px rgba(0,0,0,0.6);
                    white-space: pre-wrap;
                }

                /* الفاصل الزخرفي */
                .divider {
                    font-size: 40px;
                    color: #ffd700;
                    opacity: 0.8;
                    text-shadow: 0 2px 10px rgba(0,0,0,0.8);
                }

                .footer {
                    margin-top: 40px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                    border-top: 1px solid rgba(255, 215, 0, 0.3);
                    padding-top: 30px;
                    width: 60%;
                }

                .channel-name {
                    font-family: 'Amiri', serif;
                    font-size: 32px;
                    color: #e0e0e0;
                    text-shadow: 0 2px 5px rgba(0,0,0,1);
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 28px;
                    color: #ffd700; /* ذهبي */
                    letter-spacing: 2px;
                    direction: ltr;
                    text-shadow: 0 2px 10px rgba(0,0,0,1);
                    font-weight: 700;
                }
            </style>
        </head>
        <body>
            <!-- الطبقة المعتمة -->
            <div class="cinematic-overlay"></div>
            
            <div class="content-wrapper">
                <div class="text-body">{{ text }}</div>
                
                <!-- رمز زخرفي بسيط -->
                <div class="divider">✦</div>
                
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
        # التعامل مع Base64 أو Fallback
        if bg_data and bg_data.startswith("data:image"):
            bg_css = f"url('{bg_data}')"
            logger.info("🖼️ Rendering with AI Background (Base64)")
        else:
            bg_css = random.choice(self.fallback_gradients)
            logger.info("🎨 Rendering with Fallback Gradient")

        # تكبير الخط قليلاً لملء المساحة
        text_len = len(text)
        if text_len < 50: font_size = 110
        elif text_len < 150: font_size = 85
        elif text_len < 300: font_size = 70
        else: font_size = 55

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