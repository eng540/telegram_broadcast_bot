import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src.config import settings
from src.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Engine")

db_url = settings.DATABASE_URL

if not db_url:
    logger.critical("🚨 FATAL: DATABASE_URL is missing.")
    sys.exit(1)

# تصحيح الرابط لمكتبة SQLAlchemy
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

logger.info(f"🔌 Database Configured: PostgreSQL")

# ✅ الإعدادات الصحيحة والدقيقة لـ Supabase Transaction Pooler
# نستخدم المفتاح "statement_cache_size" فقط، وهو ما تفهمه مكتبة asyncpg
connect_args = {
    "statement_cache_size": 0
}

engine = create_async_engine(
    db_url,
    echo=False,
    poolclass=NullPool, # يمنع الاحتفاظ بالاتصالات (ضروري للمنفذ 6543)
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