#--- START OF FILE telegram_broadcast_bot-main/src/database.py ---

import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings
from src.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Engine")

db_url = settings.DATABASE_URL

if not db_url or "sqlite" in db_url:
    logger.critical("🚨 FATAL: Production requires PostgreSQL. SQLite detected.")
    sys.exit(1)

# 1. تصحيح البروتوكول تلقائياً (للتوافق مع SQLAlchemy الحديثة)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info(f"🔌 Database Configured: PostgreSQL")

# 2. إعداد المحرك (Engine Configuration)
# ✅ THE FIX: تعطيل الكاش إجبارياً (Unconditional Fix)
# هذا يمنع خطأ DuplicatePreparedStatementError بشكل قاطع بغض النظر عن المنصة
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True, # يعيد الاتصال تلقائياً إذا انقطع
    pool_size=20,
    max_overflow=10,
    connect_args={
        "statement_cache_size": 0 # تعطيل الـ Prepared Statements
    }
)

# 3. إعداد الجلسات
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database Tables Verified.")
    except Exception as e:
        logger.critical(f"❌ Database Error: {e}")
        raise e