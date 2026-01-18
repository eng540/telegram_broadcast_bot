"""
===========================================================
 Arabic Artistic Typography Engine – Auto-Repair Edition
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

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGenerator")

# ============================================================
# ثوابت التصميم
# ============================================================

CANVAS_SIZE = (1080, 1350)

SAFE_MARGINS = {
    "top": 300,
    "bottom": 300,
    "side": 180
}

COLORS = {
    "bg_fallback": (245, 240, 230),
    "text_primary": (45, 25, 10),
    "footer": (110, 90, 70)
}

# رابط الخط المباشر (Amiri Regular)
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"

# ============================================================
# الكلاس الرئيسي
# ============================================================

class ImageGenerator:
    def __init__(self):
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        
        self.font_path = os.path.join(self.assets_dir, "font.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        # التأكد من وجود المجلدات
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # --- الفحص الذكي وإصلاح الخط ---
        self._ensure_font_integrity()

    def _ensure_font_integrity(self):
        """
        يفحص وجود الخط وحجمه. إذا كان غير موجود أو تالفاً (صغير جداً)، يقوم بتحميله.
        """
        should_download = False
        
        if not os.path.exists(self.font_path):
            logger.warning("⚠️ Font file missing.")
            should_download = True
        else:
            # فحص الحجم: إذا كان الملف أقل من 50 كيلوبايت فهو تالف بالتأكيد
            file_size = os.path.getsize(self.font_path)
            if file_size < 50000: 
                logger.warning(f"⚠️ Font file is corrupted (Size: {file_size} bytes). Deleting...")
                os.remove(self.font_path)
                should_download = True
            else:
                logger.info("✅ Local font file looks healthy.")

        if should_download:
            logger.info("⬇️ Downloading fresh font from Google...")
            try:
                urllib.request.urlretrieve(FONT_URL, self.font_path)
                logger.info("✅ Font downloaded successfully!")
            except Exception as e:
                logger.critical(f"❌ Failed to download font: {e}")

    def _shape_text(self, text: str) -> str:
        configuration = {
            'delete_harakat': False,
            'support_ligatures': True,
        }
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        reshaped = reshaper.reshape(text)
        return get_display(reshaped)

    def _get_optimal_font_size(self, text_len: int) -> int:
        # أحجام كبيرة وواضحة
        if text_len < 50: return 100
        if text_len < 100: return 80
        if text_len < 200: return 65
        return 50

    def _wrap_text(self, text: str, width_px: int, font_size: int) -> List[str]:
        avg_char_w = font_size * 0.55
        chars_per_line = int(width_px / avg_char_w)
        return textwrap.wrap(text, width=chars_per_line)

    def _load_canvas(self) -> Image.Image:
        try:
            return Image.open(self.template_path).convert("RGBA")
        except Exception as e:
            logger.warning(f"⚠️ Template load failed: {e}. Using solid color.")
            return Image.new("RGBA", CANVAS_SIZE, COLORS["bg_fallback"])

    def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering card for msg {message_id}...")

        canvas = self._load_canvas()
        width, height = canvas.size
        
        # 1. تحميل الخط (بعد التأكد من سلامته)
        font_size = self._get_optimal_font_size(len(text))
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 32)
        except OSError:
            # إذا فشل التحميل رغم كل شيء، نعيد التحميل
            logger.error("❌ Font load error. Retrying download...")
            try:
                if os.path.exists(self.font_path): os.remove(self.font_path)
                urllib.request.urlretrieve(FONT_URL, self.font_path)
                font = ImageFont.truetype(self.font_path, font_size)
                footer_font = ImageFont.truetype(self.font_path, 32)
            except:
                font = ImageFont.load_default()
                footer_font = ImageFont.load_default()

        # 2. معالجة النص
        shaped_text = self._shape_text(text)
        
        # 3. التنسيق
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        lines = self._wrap_text(shaped_text, usable_width, font_size)

        line_height = int(font_size * 1.5)
        block_height = len(lines) * line_height

        start_y = SAFE_MARGINS["top"] + (height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"] - block_height) / 2

        # 4. الرسم
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        current_y = start_y

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2
            
            draw.text((x_pos, current_y), line, font=font, fill=COLORS["text_primary"])
            current_y += line_height

        # 5. التذييل
        footer_text = self._shape_text("روائع الأدب العربي")
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        footer_y = height - 200
        draw.text(((width - f_width) / 2, footer_y), footer_text, font=footer_font, fill=COLORS["footer"])

        # 6. الحفظ
        final_image = Image.alpha_composite(canvas, text_layer)
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        
        final_image.convert("RGB").save(output_path, quality=100, subsampling=0)
        
        return output_path