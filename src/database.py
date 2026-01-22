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

# 1. تصحيح البروتوكول وإضافة پارامترات الإجبار في الرابط نفسه
if "postgresql://" in db_url or "postgres://" in db_url:
    # استبدال البروتوكول
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # ✅ الحماية القصوى: إضافة پارامتر تعطيل الكاش مباشرة في رابط الاتصال
    if "?" in db_url:
        db_url += "&prepared_statement_cache_size=0"
    else:
        db_url += "?prepared_statement_cache_size=0"

logger.info(f"🔌 Database Configured with Anti-Crash Protocol")

# 2. إعداد المحرك مع تعطيل كامل لكل أنواع الكاش
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10, # تقليل حجم الحوض لتخفيف الضغط على PgBouncer
    max_overflow=5,
    connect_args={
        "statement_cache_size": 0,
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
        logger.info("✅ Database Tables Verified and Protected.")
    except Exception as e:
        logger.critical(f"❌ Database Error: {e}")
        raise e