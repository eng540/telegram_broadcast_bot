"""
===========================================================
 Arabic Artistic Typography Engine – Cinema Edition 🎬
===========================================================
"""

import os
import logging
import urllib.request
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGenerator")

# ============================================================
# إعدادات التصميم (تم تضخيم الأرقام)
# ============================================================

CANVAS_SIZE = (1080, 1350)

# هوامش جانبية كبيرة لتركيز النص في الوسط (مثل الكتب)
SAFE_MARGINS = {
    "top": 300,
    "bottom": 350,
    "side": 140  # هامش جانبي 140 بكسل
}

COLORS = {
    "bg_fallback": (245, 240, 230),
    "text_primary": (40, 20, 5),     # بني غامق
    "text_shadow": (200, 190, 180),  # ظل خفيف جداً للعمق
    "footer": (110, 90, 70)
}

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
            logger.info("⬇️ Downloading Amiri-Bold...")
            try:
                urllib.request.urlretrieve(FONT_URL, self.font_path)
            except Exception as e:
                logger.critical(f"❌ Font download failed: {e}")

    def _get_font_size(self, text_len: int) -> int:
        """
        أحجام خطوط ضخمة (Cinema Scale)
        """
        if text_len < 40: return 130   # كلمات قليلة -> خط عملاق
        if text_len < 80: return 100   # جملة قصيرة -> خط كبير جداً
        if text_len < 150: return 80   # شعر قصير -> خط كبير
        if text_len < 300: return 65   # نص متوسط
        return 55                      # نص طويل

    def _smart_wrap(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """
        خوارزمية تكسير ذكية تعتمد على قياس البكسل الفعلي وليس عدد الحروف.
        تضمن أن النص لا يخرج عن الهوامش أبداً.
        """
        lines = []
        paragraphs = text.split('\n') # احترام الأسطر الجديدة الأصلية

        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                continue
                
            current_line = []
            
            for word in words:
                # تجربة إضافة الكلمة للسطر الحالي
                test_line = ' '.join(current_line + [word])
                
                # قياس عرض السطر التجريبي
                # نستخدم reshaper هنا لأن العرض يختلف بعد التشكيل
                reshaped_test = arabic_reshaper.reshape(test_line)
                bbox = font.getbbox(reshaped_test)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    # السطر امتلأ، نحفظه ونبدأ سطراً جديداً
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            # إضافة آخر سطر في الفقرة
            if current_line:
                lines.append(' '.join(current_line))
        
        return lines

    def _load_canvas(self) -> Image.Image:
        try:
            return Image.open(self.template_path).convert("RGBA")
        except:
            return Image.new("RGBA", CANVAS_SIZE, COLORS["bg_fallback"])

    def render(self, text: str, message_id: int) -> str:
        logger.info(f"🎨 Rendering Cinema Card {message_id}...")

        canvas = self._load_canvas()
        width, height = canvas.size
        
        # 1. تحديد حجم الخط
        font_size = self._get_font_size(len(text))
        try:
            font = ImageFont.truetype(self.font_path, font_size)
            footer_font = ImageFont.truetype(self.font_path, 35)
        except:
            font = ImageFont.load_default()
            footer_font = ImageFont.load_default()

        # 2. التكسير الذكي (Smart Wrapping)
        usable_width = width - (SAFE_MARGINS["side"] * 2)
        
        # نمرر النص الخام للتكسير، ونقوم بالتشكيل لاحقاً لكل سطر
        raw_lines = self._smart_wrap(text, font, usable_width)

        # 3. حساب الارتفاعات
        line_height = int(font_size * 1.7) # تباعد أسطر كبير للفخامة
        total_block_height = len(raw_lines) * line_height
        
        # التمركز العمودي
        start_y = SAFE_MARGINS["top"] + (height - SAFE_MARGINS["top"] - SAFE_MARGINS["bottom"] - total_block_height) / 2

        # 4. الرسم
        text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        current_y = start_y

        for line in raw_lines:
            # معالجة العربية لكل سطر على حدة
            reshaped_line = arabic_reshaper.reshape(line)
            bidi_line = get_display(reshaped_line)
            
            # حساب العرض للتمركز الأفقي
            bbox = draw.textbbox((0, 0), bidi_line, font=font)
            line_width = bbox[2] - bbox[0]
            x_pos = (width - line_width) / 2
            
            # رسم ظل خفيف (Shadow)
            draw.text((x_pos + 2, current_y + 2), bidi_line, font=font, fill=COLORS["text_shadow"])
            
            # رسم النص الأساسي
            draw.text((x_pos, current_y), bidi_line, font=font, fill=COLORS["text_primary"])
            
            current_y += line_height

        # 5. التذييل
        footer_text = get_display(arabic_reshaper.reshape("روائع الأدب العربي"))
        bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
        f_width = bbox_f[2] - bbox_f[0]
        
        draw.text(((width - f_width) / 2, height - 200), footer_text, font=footer_font, fill=COLORS["footer"])

        # 6. الحفظ
        final_image = Image.alpha_composite(canvas, text_layer)
        output_path = os.path.join(self.output_dir, f"card_{message_id}.jpg")
        final_image.convert("RGB").save(output_path, quality=100)
        
        return output_path