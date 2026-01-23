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
    logger.critical("🚨 FATAL: Production requires PostgreSQL.")
    sys.exit(1)

# 1. تصحيح البروتوكول
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# ✅ إصلاح الانهيار (Critical Fix):
# إزالة أي استعلامات قديمة في الرابط لمنع تضارب القيم (Tuple Error)
if "?" in db_url:
    db_url = db_url.split("?")[0]

logger.info(f"🔌 Database Configured: Clean Protocol")

# 2. إعداد المحرك (الاعتماد فقط على connect_args)
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
    connect_args={
        # هذا يحل مشكلة PgBouncer بدون التسبب في انهيار النظام
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
        # السماح للبوت بالعمل حتى لو فشلت قاعدة البيانات جزئياً
        pass