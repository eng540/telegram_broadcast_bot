import yaml
import os
import logging
from src.config import settings

logger = logging.getLogger(__name__)

class ContentManager:
    def __init__(self, filename="messages.yaml"):
        self.filepath = os.path.join(os.path.dirname(__file__), "../resources", filename)
        self.messages = self._load_messages()

    def _load_messages(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.critical(f"❌ Failed to load messages: {e}")
            return {}

    def get(self, key_path: str, **kwargs) -> str:
        keys = key_path.split('.')
        value = self.messages
        for k in keys:
            value = value.get(k, {})
            if not value: return f"MISSING: {key_path}"
        
        format_args = {
            "bot_name": settings.CHANNEL_NAME,
            "channel_handle": settings.CHANNEL_HANDLE,
            **kwargs
        }
        if isinstance(value, str):
            return value.format(**format_args)
        return value

content = ContentManager()