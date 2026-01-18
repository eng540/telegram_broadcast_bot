import re
import logging
from telegram import Message
from src.config import settings

logger = logging.getLogger(__name__)

class FilterService:
    @staticmethod
    def is_ad(message: Message) -> bool:
        """
        فحص الرسالة: هل هي إعلان أو تحويل خارجي؟
        True = إعلان (يجب منعه)
        False = رسالة نظيفة (مسموح نشرها)
        """
        # 1. فحص مصدر التحويل (Forward Origin)
        if message.forward_origin:
            origin_chat = getattr(message.forward_origin, 'chat', None)
            # السماح فقط إذا كانت محولة من نفس القناة المصدر (تذكير بمنشور قديم)
            if origin_chat and origin_chat.id == settings.MASTER_SOURCE_ID:
                pass 
            else:
                logger.info("🚫 Filter: Blocked external forward.")
                return True

        # 2. فحص الروابط في النص
        text = message.text or message.caption or ""
        if text:
            # تعبير نمطي قوي لاكتشاف الروابط
            url_pattern = r"(https?://[^\s]+)|(t\.me/[^\s]+)|(telegram\.me/[^\s]+)"
            found_urls = re.findall(url_pattern, text)

            for url_tuple in found_urls:
                url = "".join(url_tuple).lower()
                # إذا لم يحتوي الرابط على النص المسموح به -> حظر
                if settings.ALLOWED_LINK_SUBSTRING.lower() not in url:
                    logger.info(f"🚫 Filter: Blocked external link ({url}).")
                    return True

        return False