import re
import logging
from telegram import Message
from src.config import settings

logger = logging.getLogger(__name__)

class FilterService:
    @staticmethod
    def is_ad(message: Message) -> bool:
        """
        فلتر ذكي: يمنع الروابط الخارجية والرسائل المحولة من قنوات غريبة
        """
        # 1. فحص التوجيه (Forward Check)
        # السماح فقط إذا كانت الرسالة أصلية أو محولة من نفس القناة المصدر
        fwd_origin = getattr(message, 'forward_origin', None)
        if fwd_origin:
            origin_chat = getattr(fwd_origin, 'chat', None)
            if origin_chat and origin_chat.id != settings.MASTER_SOURCE_ID:
                logger.info("🚫 Filter: Blocked external forward.")
                return True

        # الطريقة القديمة للتوجيه (للاحتياط)
        if message.forward_from_chat:
            if message.forward_from_chat.id != settings.MASTER_SOURCE_ID:
                return True

        # 2. فحص الروابط (Links Check)
        text = message.text or message.caption or ""
        if text:
            # تعبير نمطي لاكتشاف الروابط
            url_pattern = r"(https?://[^\s]+)|(t\.me/[^\s]+)|(telegram\.me/[^\s]+)"
            found_urls = re.findall(url_pattern, text)

            for url_tuple in found_urls:
                url = "".join(url_tuple).lower()
                # السماح فقط برابط قناتنا (الموجود في الإعدادات)
                if settings.CHANNEL_HANDLE.replace("@", "").lower() not in url:
                    logger.info(f"🚫 Filter: Blocked external link ({url}).")
                    return True

        return False