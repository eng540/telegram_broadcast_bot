"""
===========================================================
 Arabic Artistic Typography Engine – Strict Mode
===========================================================
"""

import os
import logging
import textwrap
import urllib.request
from typing import List

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGenerator")

# ============================================================
# إعدادات التصميم
# ============================================================

CANVAS_SIZE = (1080, 1350)
SAFE_MARGINS = {"top": 350, "bottom": 350, "side": 160}

COLORS = {
    "bg_fallback": (245, 240, 230),
    "text_primary": (40, 20, 5),     # بني غامق جداً
    "footer": (100, 80, 60)
}

# رابط الخط العريض (Bold) ليكون أوضح وأجمل
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"

# ============================================================
# الكلاس الرئيسي
# ============================================================

class ImageGenerator:
    def __init__(self):
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        
        # سنستخدم اسماً جديداً للملف لضمان عدم استخدام النسخة القديمة
        self.font_path = os.path.join(self.assets_dir, "amiri_bold_v1.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._force_download_font()

    def _force_download_font(self):
        """تحميل الخط إجبارياً"""
        if not os.path.exists(self.font_path):
            logger.info("⬇️ Downloading Amiri-Bold font...")
            try:
                urllib.request.urlretrieve(FONT_URL, self.font_path)
                logger.info("✅ Font downloaded.")
            except Exception as e:
                logger.critical(f"❌ Failed to download font: {e}")
                raise e # إيقاف النظام إذا فشل التحميل

    def _shape_text(self, text: str) -> str:
        configuration = {'delete_harakat': False, 'support_ligatures': True}
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        return get_display(reshaper.reshape(text))

    def _get_font_size(self, text_len: int) -> int:
        # أحجام كبيرة جداً
        if text_len < 50: return 110
        if text_len < 100: return 90
        if text_len < 200: return 70
        return 55

    def _wrap_text(self, text: str, width_px: int, font_size: int) -> List[str]:
        avg_char_w = font_size * 0.50
        chars_per_line = int(width_px / avg_char_w)
        return textwrap.wrap(text, width=chars_per_line)

    def _load_canvas(self) -> Image.Image:
        try:
            return Image.open(self.template_path).convert("RGBA")
        except:
            return Image.new("RGBA", CANVAS_SIZE, COLORS["bg_fallback"])

    def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering msg {message_id}...")

        canvas = self._load_canvas()
        width, height = canvas.size
        
        font_size = self._get_font_size(len(text))
        
        # --- هنا التغيير الجذري ---
        # لا يوجد try/except للخط الافتراضي.
        # يجب أن ينجح تحميل الخط العربي أو يفشل البرنامج.
        font = ImageFont.truetype(self.font_path, font_size)
        footer_font = ImageFont.truetype(self.font_path, 35)

        shaped_text = self._shape_text(text)
        
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        lines = self._wrap_text(shaped_text, usable_width, font_size)

        line_height = int(font_size * 1.6)
        block_height = len(lines) * line_height
        
        # توسيط بصري
        start_y = SAFE_MARGINS["top"] + (height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"] - block_height) / 2

        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        current_y = start_y

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2
            
            draw.text((x_pos, current_y), line, font=font, fill=COLORS["text_primary"])
            current_y += line_height

        # التذييل
        footer_text = self._shape_text("روائع الأدب العربي")
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        draw.text(((width - f_width) / 2, height - 200), footer_text, font=footer_font, fill=COLORS["footer"])

        final_image = Image.alpha_composite(canvas, text_layer)
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        final_image.convert("RGB").save(output_path, quality=100)
        
        return output_path