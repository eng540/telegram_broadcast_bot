#--- START OF FILE telegram_broadcast_bot-main/src/services/backup_service.py ---

import json
import os
import logging
from datetime import datetime
from sqlalchemy import select
from src.database import AsyncSessionLocal
# ✅ تم إزالة ScheduledPost من هنا
from src.models import BotUser, TelegramChannel, TelegramGroup, BroadcastLog

logger = logging.getLogger("BackupService")

class BackupService:
    def __init__(self):
        self.backup_dir = "/app/data/backups"
        os.makedirs(self.backup_dir, exist_ok=True)

    async def create_backup(self) -> str:
        """إنشاء ملف JSON يحتوي على بيانات النظام (بدون الجدولة)"""
        data = {
            "meta": {
                "version": "1.0",
                "date": datetime.utcnow().isoformat(),
                "type": "full_backup"
            },
            "users": [],
            "channels": [],
            "groups": []
        }

        async with AsyncSessionLocal() as session:
            # 1. نسخ المستخدمين
            users = await session.scalars(select(BotUser))
            for u in users:
                data["users"].append({
                    "user_id": u.user_id,
                    "first_name": u.first_name,
                    "username": u.username,
                    "is_active": u.is_active,
                    "joined_at": u.joined_at.isoformat() if u.joined_at else None
                })

            # 2. نسخ القنوات
            channels = await session.scalars(select(TelegramChannel))
            for c in channels:
                data["channels"].append({
                    "chat_id": c.chat_id,
                    "title": c.title,
                    "added_by_id": c.added_by_id,
                    "is_active": c.is_active,
                    "joined_at": c.joined_at.isoformat() if c.joined_at else None
                })

            # 3. نسخ المجموعات
            groups = await session.scalars(select(TelegramGroup))
            for g in groups:
                data["groups"].append({
                    "chat_id": g.chat_id,
                    "title": g.title,
                    "added_by_id": g.added_by_id,
                    "is_active": g.is_active,
                    "joined_at": g.joined_at.isoformat() if g.joined_at else None
                })

        # حفظ الملف
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return filepath

    async def restore_backup(self, filepath: str) -> str:
        """استعادة البيانات من ملف JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return f"❌ فشل قراءة الملف: {e}"

        stats = {"users": 0, "channels": 0, "groups": 0}
        
        async with AsyncSessionLocal() as session:
            # 1. استعادة المستخدمين
            for u_data in data.get("users", []):
                existing = await session.get(BotUser, u_data["user_id"])
                if not existing:
                    session.add(BotUser(
                        user_id=u_data["user_id"],
                        first_name=u_data.get("first_name"),
                        username=u_data.get("username"),
                        is_active=u_data.get("is_active", True),
                        joined_at=datetime.fromisoformat(u_data["joined_at"]) if u_data.get("joined_at") else datetime.utcnow()
                    ))
                    stats["users"] += 1
            
            # 2. استعادة القنوات
            for c_data in data.get("channels", []):
                existing = await session.get(TelegramChannel, c_data["chat_id"])
                if not existing:
                    session.add(TelegramChannel(
                        chat_id=c_data["chat_id"],
                        title=c_data.get("title"),
                        added_by_id=c_data.get("added_by_id"),
                        is_active=c_data.get("is_active", True),
                        joined_at=datetime.fromisoformat(c_data["joined_at"]) if c_data.get("joined_at") else datetime.utcnow()
                    ))
                    stats["channels"] += 1

            # 3. استعادة المجموعات
            for g_data in data.get("groups", []):
                existing = await session.get(TelegramGroup, g_data["chat_id"])
                if not existing:
                    session.add(TelegramGroup(
                        chat_id=g_data["chat_id"],
                        title=g_data.get("title"),
                        added_by_id=g_data.get("added_by_id"),
                        is_active=g_data.get("is_active", True),
                        joined_at=datetime.fromisoformat(g_data["joined_at"]) if g_data.get("joined_at") else datetime.utcnow()
                    ))
                    stats["groups"] += 1
            
            await session.commit()
            
        return (
            f"✅ تمت الاستعادة بنجاح!\n"
            f"👤 مستخدمين جدد: {stats['users']}\n"
            f"📢 قنوات جديدة: {stats['channels']}\n"
            f"🏘️ مجموعات جديدة: {stats['groups']}"
        )