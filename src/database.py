#--- START OF FILE telegram_broadcast_bot-main/src/database.py ---

import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Engine")

db_url = settings.DATABASE_URL

if not db_url or "sqlite" in db_url:
    logger.critical("🚨 FATAL: Production requires PostgreSQL. SQLite detected.")
    sys.exit(1)

# تصحيح الرابط تلقائياً
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info(f"🔌 Database Configured: PostgreSQL")

# ✅ THE FIX: إعدادات خاصة لتعطيل Prepared Statements
# هذا الكود يكتشف إذا كنا نستخدم Supabase Pooler (المنفذ 6543) ويقوم بتعطيل الكاش
# هذا يحل مشكلة: asyncpg.exceptions.InvalidSQLStatementNameError
connect_args = {}
if ":6543" in db_url or "pooler" in db_url:
    logger.info("⚙️ Supabase Transaction Pooler detected: Disabling prepared statements.")
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    connect_args=connect_args  # 👈 هنا يتم تمرير الإعدادات المصححة
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