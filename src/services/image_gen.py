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

        # التأكد من وجود مجلد المخرجات
        os.makedirs(self.output_dir, exist_ok=True)

    def create_card(self, text: str, message_id: int) -> str:
        """
        تستقبل النص وتقوم بتحويله لصورة فنية، وترجع مسار الصورة الناتجة
        """
        # 1. معالجة النص العربي (تشبيك الحروف واتجاه الكتابة)
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)

        # 2. تحميل القالب
        try:
            image = Image.open(self.bg_path)
            # التأكد من أن الصورة بنظام ألوان RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            # في حال عدم وجود القالب، ننشئ خلفية بيج سادة (احتياطي)
            print(f"Warning: Template not found ({e}), using fallback.")
            image = Image.new('RGB', (1080, 1350), color=(245, 240, 230))

        draw = ImageDraw.Draw(image)
        W, H = image.size

        # --- إعدادات التصميم (مخصصة للقالب المزخرف) ---
        
        # الهوامش الجانبية: نترك 180 بكسل من كل جانب لتفادي الزخرفة
        side_margin = 180 
        max_text_width = W - (side_margin * 2)

        # تحديد حجم الخط ديناميكياً بناءً على طول النص
        if len(text) < 100:
            font_size = 60
        elif len(text) < 200:
            font_size = 50
        else:
            font_size = 40
        
        # تحميل الخطوط
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 30)
        except:
            # خط افتراضي في حال فشل تحميل ملف الخط
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # حساب عدد الحروف في السطر الواحد (Word Wrap)
        # المعادلة: العرض المتاح / (نصف حجم الخط تقريباً)
        avg_char_width = font_size * 0.55 
        chars_per_line = int(max_text_width / avg_char_width)
        
        lines = textwrap.wrap(bidi_text, width=chars_per_line)

        # حساب الارتفاع الكلي للنص لتوسيطه عمودياً
        line_height = font_size + 20 # مسافة مريحة بين الأسطر
        total_text_height = len(lines) * line_height
        current_y = (H - total_text_height) / 2

        # لون الخط: بني داكن (Dark Coffee) ليناسب الورق القديم
        text_color = (60, 40, 20)

        # 3. رسم الأسطر
        for line in lines:
            # حساب عرض السطر الحالي لتوسيطه أفقياً
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (W - line_width) / 2
            
            draw.text((x_pos, current_y), line, font=font, fill=text_color)
            current_y += line_height

        # 4. إضافة التذييل (Footer)
        footer_text = "روائع الأدب العربي"
        footer_reshaped = get_display(arabic_reshaper.reshape(footer_text))
        
        bbox_f = draw.textbbox((0, 0), footer_reshaped, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        # رسم التذييل في الأسفل (مرفوع 150 بكسل عن القاع لتفادي الزخرفة السفلية)
        draw.text(((W - f_width) / 2, H - 150), footer_reshaped, font=footer_font, fill=(100, 80, 60))

        # 5. حفظ الصورة
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        image.save(output_path, quality=95)
        
        return output_path