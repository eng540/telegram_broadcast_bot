import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool # ✅ الإضافة الضرورية
from src.config import settings
from src.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Engine")

db_url = settings.DATABASE_URL

if not db_url:
    logger.critical("🚨 FATAL: DATABASE_URL is missing.")
    sys.exit(1)

# تصحيح الرابط
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

logger.info(f"🔌 Database Configured: PostgreSQL")

# إعدادات خاصة لـ Supabase Pooler
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0
}

engine = create_async_engine(
    db_url,
    echo=False,
    # ✅ استخدام NullPool يمنع الاحتفاظ بالاتصالات القديمة ويحل مشكلة التضارب
    poolclass=NullPool, 
    connect_args=connect_args
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database Tables Verified.")
    except Exception as e:
        logger.critical(f"❌ Database Error: {e}")
        raise e