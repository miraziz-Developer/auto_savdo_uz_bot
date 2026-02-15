"""
Database connection and session management — Optimized for Free Tier
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from loguru import logger

from config import settings
from database.models import Base


# Create async engine — OPTIMIZED for Free Tier (512MB RAM)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=3,           # Was 10 — 3 is enough for single-bot
    max_overflow=2,        # Was 20 — minimal overflow
    pool_recycle=1800,     # Recycle every 30 min (was 60 min)
    pool_timeout=10,       # Timeout 10 sec (don't hang forever)
    pool_pre_ping=True,    # Check connection health before use
    connect_args={
        "command_timeout": 10,      # Query timeout 10 sec
        "server_settings": {
            "statement_timeout": "15000",  # 15 sec max per statement
        }
    }
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database - create all tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
