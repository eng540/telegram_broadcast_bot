from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Boolean, DateTime, String, ForeignKey
from datetime import datetime

class Base(DeclarativeBase):
    pass

# --- 1. الكيان البشري (المشترك / المالك) ---
class BotUser(Base):
    __tablename__ = "bot_users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # علاقات عكسية (لمعرفة ماذا يملك هذا الشخص)
    # channels = relationship("TelegramChannel", back_populates="owner")
    # groups = relationship("TelegramGroup", back_populates="owner")

# --- 2. كيان القنوات (Channels) ---
class TelegramChannel(Base):
    __tablename__ = "channels"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    
    # من هو الشخص الذي أضاف البوت لهذه القناة؟ (كنز المعلومات)
    added_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bot_users.user_id"), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- 3. كيان المجموعات (Groups) ---
class TelegramGroup(Base):
    __tablename__ = "groups"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    
    # من هو الشخص الذي أضاف البوت للمجموعة؟
    added_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bot_users.user_id"), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)