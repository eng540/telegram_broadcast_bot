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
        (متوافق مع python-telegram-bot v21+)
        """
        
        # --- 1. فحص التوجيه (Forward Check) - التحديث الجديد ---
        # في النسخة 21+، نستخدم forward_origin بدلاً من forward_from_chat
        if message.forward_origin:
            # نحاول معرفة القناة الأصلية
            origin_chat = getattr(message.forward_origin, 'chat', None)
            
            # إذا كانت الرسالة محولة من قناة، وهذه القناة ليست قناتنا المصدر -> حظر
            if origin_chat and origin_chat.id != settings.MASTER_SOURCE_ID:
                logger.info("🚫 Filter: Blocked external forward (Channel).")
                return True
            
            # إذا كانت محولة من مستخدم أو مصدر مخفي -> حظر (غالباً إعلانات)
            if not origin_chat:
                 logger.info("🚫 Filter: Blocked external forward (User/Hidden).")
                 return True

        # --- 2. فحص الروابط (Links Check) ---
        text = message.text or message.caption or ""
        if text:
            # تعبير نمطي لاكتشاف الروابط
            url_pattern = r"(https?://[^\s]+)|(t\.me/[^\s]+)|(telegram\.me/[^\s]+)"
            found_urls = re.findall(url_pattern, text)

            for url_tuple in found_urls:
                url = "".join(url_tuple).lower()
                
                # تنظيف المعرف من @ للمقارنة
                my_handle = settings.CHANNEL_HANDLE.replace("@", "").lower()
                
                # إذا وجد رابطاً، ولم يكن يحتوي على معرف قناتنا -> حظر
                if my_handle not in url:
                    logger.info(f"🚫 Filter: Blocked external link ({url}).")
                    return True

        return False