import textwrap
import os
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

class ImageGenerator:
    def __init__(self):
        # المسارات داخل الحاوية (Docker Container)
        self.assets_dir = "/app/assets"
        self.font_path = os.path.join(self.assets_dir, "font.ttf")
        self.bg_path = os.path.join(self.assets_dir, "template.jpg")
        self.output_dir = "/app/data" # مكان حفظ الصور المؤقتة

    def create_card(self, text: str, message_id: int) -> str:
        """
        تستقبل النص وتقوم بتحويله لصورة، وترجع مسار الصورة الناتجة
        """
        # 1. معالجة النص العربي
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)

        # 2. تحميل القالب
        try:
            image = Image.open(self.bg_path)
        except Exception:
            # خلفية احتياطية في حال فشل تحميل الصورة
            image = Image.new('RGB', (1080, 1080), color=(240, 240, 240))

        draw = ImageDraw.Draw(image)
        W, H = image.size

        # 3. تحديد حجم الخط ديناميكياً بناءً على طول النص
        font_size = 60
        if len(text) > 100: font_size = 50
        if len(text) > 200: font_size = 40
        
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 30)
        except:
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # 4. تغليف النص (Word Wrap)
        # نقدر عدد الحروف في السطر (تقريبي)
        chars_per_line = int((W - 140) / (font_size * 0.5)) 
        lines = textwrap.wrap(bidi_text, width=chars_per_line)

        # 5. حساب الإحداثيات لتوسيط النص
        line_height = font_size + 15
        total_text_height = len(lines) * line_height
        current_y = (H - total_text_height) / 2

        # 6. رسم السطور
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (W - line_width) / 2
            
            # رسم النص (لون أسود داكن)
            draw.text((x_pos, current_y), line, font=font, fill=(40, 40, 40))
            current_y += line_height

        # 7. إضافة التذييل (Footer)
        footer_text = "قناة روائع الأدب العربي"  # يمكنك تغيير هذا النص
        footer_reshaped = get_display(arabic_reshaper.reshape(footer_text))
        
        # رسم التذييل في الأسفل
        bbox_f = draw.textbbox((0, 0), footer_reshaped, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        draw.text(((W - f_width) / 2, H - 100), footer_reshaped, font=footer_font, fill=(100, 100, 100))

        # 8. الحفظ
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        image.save(output_path, quality=95)
        return output_path