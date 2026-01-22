# --- START OF FILE src/database.py ---

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

# ---------------------------------------------------------
# ✅ THE NUCLEAR FIX (الحل الجذري)
# تعديل الرابط لفرض تعطيل الكاش على مستوى البروتوكول
# ---------------------------------------------------------

# 1. تصحيح البروتوكول
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# 2. حقن إعدادات PgBouncer داخل الرابط مباشرة
# هذا يضمن أن asyncpg يرى الإعداد حتى لو تجاهل connect_args
if "?" in db_url:
    db_url += "&statement_cache_size=0&prepared_statement_cache_size=0"
else:
    db_url += "?statement_cache_size=0&prepared_statement_cache_size=0"

logger.info(f"🔌 Database Configured with FORCED NO-CACHE Protocol")

# 3. إعداد المحرك
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    # تقليل حجم الـ Pool لتخفيف التصادمات في PgBouncer
    pool_size=5,
    max_overflow=10,
    # الإبقاء على connect_args كخط دفاع ثاني
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "command_timeout": 60
    }
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database Tables Verified.")
    except Exception as e:
        logger.critical(f"❌ Database Error: {e}")
        # لن نوقف النظام، سنحاول الاستمرار
        # raise e