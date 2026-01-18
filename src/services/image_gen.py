"""
===========================================================
 Arabic Artistic Typography Engine – Ultimate Edition
 Integrated with Zajel Bot System
===========================================================
"""

import os
import logging
import textwrap
from enum import Enum
from typing import List

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# ============================================================
# Logging Configuration
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGenerator")

# ============================================================
# Constants & Design System
# ============================================================
CANVAS_SIZE = (1080, 1350)
# هوامش آمنة لتفادي الزخارف
SAFE_MARGINS = dict(top=200, bottom=250, side=180)

BASE_BG_COLOR = (245, 240, 230)
TEXT_PRIMARY = (60, 40, 20)    # بني داكن
TEXT_SECONDARY = (120, 90, 60) # بني فاتح للتذييل
SHADOW_COLOR = (0, 0, 0, 80)   # ظل خفيف

LINE_HEIGHT_RATIO = 1.5
CHAR_WIDTH_RATIO = 0.55
OUTPUT_QUALITY = 95

# ============================================================
# Theme System
# ============================================================
class Theme(Enum):
    CLASSIC = "classic"
    LUXURY = "luxury"

THEME_EFFECTS = {
    Theme.CLASSIC: dict(shadow=False, glow=False),
    Theme.LUXURY: dict(shadow=True, glow=False), # الظل يعطي فخامة للقراءة
}

# ============================================================
# Core Class
# ============================================================
class ImageGenerator:
    def __init__(self):
        # مسارات دوكر الثابتة
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        
        self.font_path = os.path.join(self.assets_dir, "font.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        # التأكد من المجلدات
        os.makedirs(self.output_dir, exist_ok=True)
        
        # الإعداد الافتراضي
        self.current_theme = Theme.LUXURY

    def _shape_arabic(self, text: str) -> str:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def _detect_layout(self, text: str) -> str:
        """تحديد هل النص شعر أم نثر لضبط التنسيق"""
        if "\n" in text or len(text) < 60:
            return "poetry"
        return "quote"

    def _optimal_font_size(self, length: int) -> int:
        if length < 80: return 65
        if length < 150: return 55
        if length < 250: return 45
        return 40

    def _wrap_balanced(self, text: str, width_px: int, font_size: int) -> List[str]:
        # حساب تقريبي لعدد الحروف في السطر
        chars = max(int(width_px / (font_size * CHAR_WIDTH_RATIO)), 10)
        return textwrap.wrap(text, width=chars)

    def _load_canvas(self) -> Image.Image:
        try:
            return Image.open(self.template_path).convert("RGBA")
        except Exception as e:
            logger.warning(f"Template not found ({e}), using fallback.")
            return Image.new("RGBA", CANVAS_SIZE, BASE_BG_COLOR)

    def _draw_shadow(self, draw, pos, text, font):
        x, y = pos
        # رسم الظل مزاحاً بمقدار 3 بكسل
        draw.text((x+3, y+3), text, font=font, fill=SHADOW_COLOR)

    def create_card(self, text: str, message_id: int) -> str:
        """
        الدالة الرئيسية التي يستدعيها البوت
        """
        logger.info(f"🎨 Rendering artwork for msg {message_id}...")

        # 1. تجهيز اللوحة
        canvas = self._load_canvas()
        width, height = canvas.size
        
        # 2. تجهيز النص
        shaped_text = self._shape_arabic(text)
        font_size = self._optimal_font_size(len(text))
        
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 30)
        except:
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # 3. حساب المساحات
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        usable_height = height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"]

        lines = self._wrap_balanced(shaped_text, usable_width, font_size)

        line_h = int(font_size * LINE_HEIGHT_RATIO)
        block_h = len(lines) * line_h
        
        # التمركز العمودي
        start_y = SAFE_MARGINS["top"] + (usable_height - block_h) / 2

        # 4. الرسم (طبقة النصوص)
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        current_y = start_y
        effects = THEME_EFFECTS[self.current_theme]

        for line in lines:
            # حساب عرض السطر للتمركز الأفقي
            bbox = text_draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            x = (width - line_w) / 2

            # رسم الظل أولاً (إذا كان مفعلاً)
            if effects["shadow"]:
                self._draw_shadow(text_draw, (x, current_y), line, font)

            # رسم النص الأصلي
            text_draw.text((x, current_y), line, font=font, fill=TEXT_PRIMARY)
            current_y += line_h

        # 5. دمج الطبقات
        # دمج النص مع الخلفية
        final_image = Image.alpha_composite(canvas, text_layer)

        # 6. التذييل (Footer)
        footer_text = self._shape_arabic("روائع الأدب العربي")
        draw_final = ImageDraw.Draw(final_image)
        
        bbox_f = draw_final.textbbox((0, 0), footer_text, font=footer_font)
        f_w = bbox_f[2] - bbox_f[0]
        
        draw_final.text(
            ((width - f_w) / 2, height - 150),
            footer_text,
            font=footer_font,
            fill=TEXT_SECONDARY
        )

        # 7. الحفظ
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        # التحويل إلى RGB قبل الحفظ كـ JPEG
        final_image.convert("RGB").save(output_path, quality=OUTPUT_QUALITY)

        return output_path