"""
===========================================================
 Arabic Artistic Typography Engine – Fixed & Amplified
===========================================================
"""

import os
import logging
import textwrap
from typing import List

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# إعداد السجلات
logger = logging.getLogger("ImageGenerator")

# ============================================================
# ثوابت التصميم (تم تكبير القيم بشكل ضخم)
# ============================================================

CANVAS_SIZE = (1080, 1350)
SAFE_MARGINS = {
    "top": 300,    # نزلنا البداية لتكون في قلب الورقة
    "bottom": 300,
    "side": 150    # هوامش جانبية أضيق لترك مساحة للنص
}

COLORS = {
    "bg_fallback": (245, 240, 230),
    "text_primary": (45, 25, 10),    # بني غامق جداً للقراءة
    "footer": (100, 80, 60)
}

# ============================================================
# الكلاس الرئيسي
# ============================================================

class ImageGenerator:
    def __init__(self):
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        
        self.font_path = os.path.join(self.assets_dir, "font.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # فحص وجود الخط (مهم جداً)
        if not os.path.exists(self.font_path):
            logger.critical(f"❌ FONT NOT FOUND AT: {self.font_path}")
            # سنحاول البحث في المسار المحلي في حال كنا نشغل محلياً
            if os.path.exists("assets/font.ttf"):
                self.font_path = "assets/font.ttf"

    def _shape_text(self, text: str) -> str:
        configuration = {
            'delete_harakat': False,
            'support_ligatures': True,
        }
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        reshaped = reshaper.reshape(text)
        return get_display(reshaped)

    def _get_optimal_font_size(self, text_len: int) -> int:
        """أحجام خطوط ضخمة لضمان الوضوح"""
        if text_len < 50: return 110   # ضخم جداً للعبارات القصيرة
        if text_len < 100: return 90   # كبير للمتوسطة
        if text_len < 200: return 70   # مناسب للشعر
        return 55                      # للنصوص الطويلة

    def _wrap_text(self, text: str, width_px: int, font_size: int) -> List[str]:
        # تعديل معامل العرض لأن الخط العربي عريض
        avg_char_w = font_size * 0.5 
        chars_per_line = int(width_px / avg_char_w)
        return textwrap.wrap(text, width=chars_per_line)

    def _load_canvas(self) -> Image.Image:
        try:
            return Image.open(self.template_path).convert("RGBA")
        except Exception as e:
            logger.warning(f"⚠️ Template error: {e}")
            return Image.new("RGBA", CANVAS_SIZE, COLORS["bg_fallback"])

    def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering card for msg {message_id}...")

        canvas = self._load_canvas()
        width, height = canvas.size
        
        # 1. تجهيز الخط (مع إجبار الخطأ إذا فشل)
        font_size = self._get_optimal_font_size(len(text))
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 35)
        except OSError:
            logger.error("❌ CRITICAL: Could not load font file! Using default (UGLY).")
            # محاولة أخيرة لتحميل أي خط عربي بالنظام (نادراً ما ينجح في دوكر)
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # 2. معالجة النص
        shaped_text = self._shape_text(text)
        
        # 3. حساب المساحات
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        lines = self._wrap_text(shaped_text, usable_width, font_size)

        # حساب ارتفاع الكتلة النصية
        line_height = int(font_size * 1.5) # تباعد أسطر مريح
        block_height = len(lines) * line_height

        # التمركز العمودي
        start_y = (height - block_height) / 2 - 50 # رفعنا النص قليلاً للأعلى (Optical Center)

        # 4. الرسم
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        current_y = start_y

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2
            
            # رسم النص
            draw.text((x_pos, current_y), line, font=font, fill=COLORS["text_primary"])
            current_y += line_height

        # 5. التذييل
        footer_text = self._shape_text("روائع الأدب العربي")
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        draw.text(((width - f_width) / 2, height - 180), footer_text, font=footer_font, fill=COLORS["footer"])

        # 6. الحفظ
        final_image = Image.alpha_composite(canvas, text_layer)
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        final_image.convert("RGB").save(output_path, quality=100)
        
        return output_path