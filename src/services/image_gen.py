"""
===========================================================
 Arabic Artistic Typography Engine – Production Fixed
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGenerator")

# ============================================================
# ثوابت التصميم (تم تكبير القيم لتناسب دقة 1080x1350)
# ============================================================

CANVAS_SIZE = (1080, 1350)

# الهوامش الآمنة (تم توسيعها لتبتعد عن الزخارف الجانبية)
SAFE_MARGINS = {
    "top": 300,     # ترك مساحة كبيرة في الأعلى
    "bottom": 300,  # ترك مساحة في الأسفل
    "side": 180     # هامش جانبي عريض لعدم ملامسة الإطار
}

COLORS = {
    "bg_fallback": (245, 240, 230),
    "text_primary": (45, 25, 10),    # بني غامق جداً (Dark Coffee)
    "footer": (110, 90, 70)          # بني فاتح للتذييل
}

# ============================================================
# الكلاس الرئيسي
# ============================================================

class ImageGenerator:
    def __init__(self):
        # مسارات Docker القياسية
        self.assets_dir = "/app/assets"
        self.output_dir = "/app/data"
        
        self.font_path = os.path.join(self.assets_dir, "font.ttf")
        self.template_path = os.path.join(self.assets_dir, "template.jpg")
        
        # إنشاء مجلد المخرجات
        os.makedirs(self.output_dir, exist_ok=True)
        
        # --- تشخيص النظام (System Diagnostics) ---
        # هذا الكود سيطبع محتويات المجلد في السجلات لنعرف هل انتقلت الملفات أم لا
        try:
            if os.path.exists(self.assets_dir):
                files = os.listdir(self.assets_dir)
                logger.info(f"📂 ASSETS CHECK: Found files: {files}")
                
                if "font.ttf" not in files:
                    logger.critical("❌ CRITICAL: 'font.ttf' is MISSING from assets folder!")
                else:
                    logger.info("✅ Font file detected.")
            else:
                logger.critical(f"❌ CRITICAL: Assets directory {self.assets_dir} does not exist!")
        except Exception as e:
            logger.error(f"⚠️ Error checking assets: {e}")

    def _shape_text(self, text: str) -> str:
        """معالجة النص العربي"""
        configuration = {
            'delete_harakat': False,
            'support_ligatures': True,
        }
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        reshaped = reshaper.reshape(text)
        return get_display(reshaped)

    def _get_optimal_font_size(self, text_len: int) -> int:
        """
        حساب حجم الخط.
        تم تكبير الأرقام بشكل كبير لأن الصورة السابقة أظهرت خطاً صغيراً جداً.
        """
        if text_len < 50: return 100   # ضخم جداً للعبارات القصيرة
        if text_len < 100: return 80   # كبير
        if text_len < 200: return 65   # متوسط (للشعر)
        return 50                      # للنصوص الطويلة

    def _wrap_text(self, text: str, width_px: int, font_size: int) -> List[str]:
        """تكسير النص لأسطر"""
        # الخط العربي عريض، لذا نضرب الحجم في 0.55 لتقدير عرض الحرف
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
        
        # 1. تحميل الخط (مع معالجة الأخطاء)
        font_size = self._get_optimal_font_size(len(text))
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 32)
        except OSError:
            logger.error("❌ FONT LOAD FAILED! Using default font (Will look bad).")
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # 2. معالجة النص
        shaped_text = self._shape_text(text)
        
        # 3. حساب المساحات
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        lines = self._wrap_text(shaped_text, usable_width, font_size)

        # حساب ارتفاع الكتلة النصية
        line_height = int(font_size * 1.5) # تباعد أسطر مريح (1.5x)
        block_height = len(lines) * line_height

        # التمركز العمودي (Optical Center)
        # نرفع النص قليلاً (50px) ليبدو متوازناً بصرياً
        start_y = SAFE_MARGINS["top"] + (height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"] - block_height) / 2

        # 4. الرسم
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        current_y = start_y

        for line in lines:
            # حساب عرض السطر للتمركز الأفقي
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2
            
            # رسم النص
            draw.text((x_pos, current_y), line, font=font, fill=COLORS["text_primary"])
            current_y += line_height

        # 5. التذييل (Footer)
        footer_text = self._shape_text("روائع الأدب العربي")
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        # رسم التذييل في الأسفل (فوق الزخرفة السفلية)
        footer_y = height - 200
        draw.text(((width - f_width) / 2, footer_y), footer_text, font=footer_font, fill=COLORS["footer"])

        # 6. الحفظ
        final_image = Image.alpha_composite(canvas, text_layer)
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        
        # حفظ بجودة قصوى
        final_image.convert("RGB").save(output_path, quality=100, subsampling=0)
        
        return output_path