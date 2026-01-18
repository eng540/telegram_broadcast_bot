"""
===========================================================
 Arabic Artistic Typography Engine – Native Raqm Mode
===========================================================
"""

import os
import logging
import urllib.request
from PIL import Image, ImageDraw, ImageFont

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGenerator")

# ============================================================
# إعدادات التصميم
# ============================================================

CANVAS_SIZE = (1080, 1350)
SAFE_MARGINS = {"top": 350, "bottom": 350, "side": 160}

COLORS = {
    "bg_fallback": (245, 240, 230),
    "text_primary": (40, 20, 5),
    "footer": (100, 80, 60)
}

# رابط الخط
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"

class ImageGenerator:
    def __init__(self):
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        self.font_path = os.path.join(self.assets_dir, "amiri_bold.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._ensure_font()

    def _ensure_font(self):
        if not os.path.exists(self.font_path) or os.path.getsize(self.font_path) < 10000:
            logger.info("⬇️ Downloading font...")
            try:
                urllib.request.urlretrieve(FONT_URL, self.font_path)
                logger.info("✅ Font downloaded.")
            except Exception as e:
                logger.critical(f"❌ Font download failed: {e}")

    def _load_canvas(self) -> Image.Image:
        try:
            return Image.open(self.template_path).convert("RGBA")
        except:
            return Image.new("RGBA", CANVAS_SIZE, COLORS["bg_fallback"])

    def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering msg {message_id} using Native Raqm...")

        canvas = self._load_canvas()
        width, height = canvas.size
        
        # تحديد حجم الخط
        text_len = len(text)
        if text_len < 50: font_size = 100
        elif text_len < 100: font_size = 80
        elif text_len < 200: font_size = 65
        else: font_size = 50

        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 35)
        except OSError as e:
            logger.critical(f"❌ FAILED TO LOAD FONT: {e}")
            # لن نكمل إذا فشل الخط، لكي لا نرسل صورة مشوهة
            raise e

        draw = ImageDraw.Draw(canvas)

        # --- الرسم باستخدام ميزات Pillow الحديثة (بدون reshaper) ---
        # نستخدم direction='rtl' و language='ar'
        # هذا يتطلب وجود libraqm في النظام (وهو ما أضفناه في Dockerfile)
        
        # حساب المساحة المتاحة
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        
        # التمركز والتقسيم
        # ملاحظة: مع libraqm، التكسير اليدوي (textwrap) قد يحتاج لضبط
        # سنستخدم طريقة بسيطة للرسم في المنتصف
        
        # بما أن textwrap لا يدعم RTL بشكل كامل، سنستخدمه بحذر
        import textwrap
        avg_char_w = font_size * 0.5
        chars_per_line = int(usable_width / avg_char_w)
        lines = textwrap.wrap(text, width=chars_per_line)
        
        line_height = int(font_size * 1.5)
        block_height = len(lines) * line_height
        start_y = SAFE_MARGINS["top"] + (height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"] - block_height) / 2
        
        current_y = start_y
        
        for line in lines:
            # استخدام features='rtla' لتفعيل الخصائص العربية
            # استخدام direction='rtl'
            bbox = draw.textbbox((0, 0), line, font=font, direction='rtl', language='ar')
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2
            
            draw.text((x_pos, current_y), line, font=font, fill=COLORS["text_primary"], direction='rtl', language='ar')
            current_y += line_height

        # التذييل
        footer_text = "روائع الأدب العربي"
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font, direction='rtl', language='ar')
        f_width = bbox_f[2] - bbox_f[0]
        
        draw.text(((width - f_width) / 2, height - 200), footer_text, font=footer_font, fill=COLORS["footer"], direction='rtl', language='ar')

        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        canvas.convert("RGB").save(output_path, quality=100)
        
        return output_path