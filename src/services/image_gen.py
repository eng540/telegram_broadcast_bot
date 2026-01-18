"""
===========================================================
 Arabic Artistic Typography Engine – Ultimate Edition
===========================================================
"""

import os
import logging
import textwrap
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# إعداد السجلات
logger = logging.getLogger("ImageGenerator")

# ============================================================
# ثوابت التصميم (Design System)
# ============================================================

CANVAS_SIZE = (1080, 1350)  # 4:5 Aspect Ratio
# الهوامش الآمنة (تم ضبطها خصيصاً لقالب الزخرفة الخاص بك)
SAFE_MARGINS = {
    "top": 220,
    "bottom": 280,
    "side": 190
}

# لوحة الألوان (Color Palette)
COLORS = {
    "bg_fallback": (245, 240, 230),  # بيج ورقي
    "text_primary": (50, 30, 15),    # بني قهوة داكن
    "text_shadow": (200, 180, 160),  # ظل فاتح للحفر
    "footer": (110, 90, 70)          # بني متوسط للتذييل
}

# إعدادات الخطوط
LINE_HEIGHT_RATIO = 1.6  # مسافة واسعة بين الأسطر للفخامة
CHAR_WIDTH_RATIO = 0.55  # معامل عرض الحرف العربي

# ============================================================
# الكلاس الرئيسي
# ============================================================

class ImageGenerator:
    def __init__(self):
        # مسارات Docker
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        
        self.font_path = os.path.join(self.assets_dir, "font.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        # التأكد من وجود مجلد المخرجات
        os.makedirs(self.output_dir, exist_ok=True)

    def _shape_text(self, text: str) -> str:
        """معالجة النص العربي (تشبيك + اتجاه)"""
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def _get_optimal_font_size(self, text_len: int) -> int:
        """حساب حجم الخط بناءً على طول النص للحفاظ على التوازن"""
        if text_len < 60: return 70   # نصوص قصيرة جداً (حكم)
        if text_len < 120: return 60  # نصوص متوسطة
        if text_len < 200: return 50  # شعر متوسط
        return 42                     # نصوص طويلة

    def _wrap_text(self, text: str, width_px: int, font_size: int) -> List[str]:
        """تكسير النص إلى أسطر متوازنة بصرياً"""
        # تقدير عدد الحروف في السطر
        avg_char_w = font_size * CHAR_WIDTH_RATIO
        chars_per_line = int(width_px / avg_char_w)
        return textwrap.wrap(text, width=chars_per_line)

    def _load_canvas(self) -> Image.Image:
        """تحميل القالب أو إنشاء بديل في حال الفقدان"""
        try:
            return Image.open(self.template_path).convert("RGBA")
        except Exception as e:
            logger.warning(f"⚠️ Template not found: {e}. Using fallback.")
            return Image.new("RGBA", CANVAS_SIZE, COLORS["bg_fallback"])

    def _draw_text_with_shadow(self, draw, pos, text, font):
        """رسم النص مع ظل خفيف لزيادة الوضوح والفخامة"""
        x, y = pos
        # رسم الظل (مزاح 2 بكسل)
        # draw.text((x+2, y+2), text, font=font, fill=COLORS["text_shadow"])
        # رسم النص الأساسي
        draw.text((x, y), text, font=font, fill=COLORS["text_primary"])

    def render(self, text: str, message_id: int) -> str:
        """
        الدالة الرئيسية لتوليد البطاقة
        """
        logger.info(f"🎨 Rendering card for msg {message_id}...")

        # 1. الإعداد
        canvas = self._load_canvas()
        width, height = canvas.size
        
        shaped_text = self._shape_text(text)
        font_size = self._get_optimal_font_size(len(text))

        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 32)
        except:
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # 2. حساب المساحات
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        usable_height = height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"]

        lines = self._wrap_text(shaped_text, usable_width, font_size)

        # حساب ارتفاع الكتلة النصية
        line_height = int(font_size * LINE_HEIGHT_RATIO)
        block_height = len(lines) * line_height

        # 3. التمركز (Centering Logic)
        # حساب نقطة البداية العمودية لتكون في المنتصف تماماً
        start_y = SAFE_MARGINS["top"] + (usable_height - block_height) / 2
        
        # إنشاء طبقة شفافة للنص
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        current_y = start_y

        # 4. الرسم
        for line in lines:
            # حساب عرض السطر للتمركز الأفقي
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2

            self._draw_text_with_shadow(draw, (x_pos, current_y), line, font)
            current_y += line_height

        # 5. التذييل (Footer)
        footer_text = self._shape_text("روائع الأدب العربي")
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        # رسم التذييل في المنطقة السفلية الآمنة
        footer_y = height - 180
        draw.text(((width - f_width) / 2, footer_y), footer_text, font=footer_font, fill=COLORS["footer"])

        # 6. الدمج والحفظ
        final_image = Image.alpha_composite(canvas, text_layer)
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        
        # الحفظ بجودة عالية جداً
        final_image.convert("RGB").save(output_path, quality=100, subsampling=0)
        
        return output_path