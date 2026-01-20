from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Boolean, DateTime, String, ForeignKey, Integer
from datetime import datetime

class Base(DeclarativeBase):
    pass

class BotUser(Base):
    __tablename__ = "bot_users"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TelegramChannel(Base):
    __tablename__ = "channels"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    added_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bot_users.user_id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TelegramGroup(Base):
    __tablename__ = "groups"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    added_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bot_users.user_id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- الجدول الجديد: سجل الرسائل ---
class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_msg_id: Mapped[int] = mapped_column(BigInteger, index=True) # رقم الرسالة في القناة الأم
    target_chat_id: Mapped[int] = mapped_column(BigInteger, index=True) # أين أرسلناها؟
    target_msg_id: Mapped[int] = mapped_column(BigInteger) # ما هو رقمها هناك؟
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)