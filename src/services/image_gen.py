#--- START OF FILE telegram_broadcast_bot-main/src/services/image_gen.py ---

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
        
        # ✅ شبكة الأمان: تدرجات لونية فخمة (لا تفشل أبداً)
        # ستظهر هذه الخلفيات فقط إذا فشل الذكاء الاصطناعي في تحميل الصورة
        self.fallback_gradients = [
            "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)", # أزرق ملكي
            "linear-gradient(135deg, #3a1c71 0%, #d76d77 50%, #ffaf7b 100%)", # غروب
            "linear-gradient(135deg, #134e5e 0%, #71b280 100%)", # أخضر زمردي
            "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)", # داكن فخم
            "linear-gradient(135deg, #4b6cb7 0%, #182848 100%)", # أزرق ليلي
            "linear-gradient(135deg, #232526 0%, #414345 100%)"  # رمادي معدني
        ]

    def _create_template(self):
        os.makedirs(self.template_dir, exist_ok=True)
        
        # تصميم سينمائي مع طبقة تعتيم لضمان قراءة النص
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
                    
                    /* الخلفية الأساسية (تدرج لوني) تظهر دائماً كاحتياط */
                    background: {{ fallback_gradient }};
                    
                    /* الخلفية المركبة: تدرج تعتيم + صورة الذكاء الاصطناعي */
                    background-image: 
                        linear-gradient(to bottom, rgba(0,0,0,0.2), rgba(0,0,0,0.8)), 
                        {{ bg_image_css }};
                        
                    background-size: cover;
                    background-position: center;
                    background-blend-mode: normal;
                    
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }

                .content-wrapper {
                    width: 850px;
                    padding: 60px 40px;
                    text-align: center;
                    color: #fff;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 30px;
                    
                    /* تأثير زجاجي خفيف جداً */
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(5px);
                    border-radius: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }

                .text-body {
                    font-size: {{ font_size }}px;
                    font-weight: 700;
                    line-height: 1.8;
                    /* ظل قوي للنص لضمان القراءة */
                    text-shadow: 0 4px 15px rgba(0,0,0,1);
                    white-space: pre-wrap;
                }

                .footer {
                    margin-top: 30px;
                    border-top: 2px solid rgba(255,215,0, 0.5); /* خط ذهبي */
                    padding-top: 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }

                .channel-name {
                    font-family: 'Amiri', serif;
                    font-size: 26px;
                    color: #e0e0e0;
                    margin-bottom: 5px;
                }

                .handle {
                    font-family: 'Reem Kufi', sans-serif;
                    font-size: 28px;
                    color: #ffd700; /* ذهبي */
                    letter-spacing: 2px;
                    direction: ltr;
                    font-weight: 700;
                    text-shadow: 0 2px 5px rgba(0,0,0,1);
                }
            </style>
        </head>
        <body>
            <div class="content-wrapper">
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
        # إعداد متغيرات الخلفية
        bg_image_css = "none" # الافتراضي: لا توجد صورة
        
        # 1. التحقق من وجود الصورة محلياً
        if bg_path and os.path.exists(bg_path):
            # تحويل المسار إلى مسار مطلق (Absolute Path) ليفهمه المتصفح
            abs_path = os.path.abspath(bg_path)
            bg_image_css = f"url('file://{abs_path}')"
            logger.info(f"🖼️ Rendering with local background: {abs_path}")
        else:
            logger.warning("⚠️ No background file found. Using fallback gradient.")

        # 2. اختيار تدرج لوني عشوائي (يظهر خلف الصورة أو كبديل لها)
        fallback_gradient = random.choice(self.fallback_gradients)

        # 3. ضبط حجم الخط ديناميكياً
        text_len = len(text)
        if text_len < 50: font_size = 95
        elif text_len < 150: font_size = 75
        elif text_len < 300: font_size = 60
        else: font_size = 50

        # 4. التجهيز
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("card.html")
        
        html_out = template.render(
            text=text, 
            font_size=font_size, 
            bg_image_css=bg_image_css, # نمرر CSS URL الجاهز
            fallback_gradient=fallback_gradient
        )
        
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")

        # 5. التصوير (الرسم)
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
            
            await page.set_content(html_out)
            
            # انتظار قصير للتأكد من تحميل الصورة المحلية
            await page.wait_for_timeout(1000) 
            
            await page.screenshot(path=output_path, type='jpeg', quality=95)
            await browser.close()
            
        return output_path