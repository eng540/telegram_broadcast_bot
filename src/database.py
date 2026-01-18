from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import Base

# استخدام pool_recycle لمنع انقطاع الاتصال الطويل
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False,
    pool_recycle=3600
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)