"""
Database connection and session management — Optimized v2
Connection pooling, health checks, graceful error handling
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from loguru import logger

from config import settings
from database.models import Base


# ──────────────────────────────────────────────
# ENGINE — connection pool sozlamalari
# ──────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    # Pool: 1 bot uchun 3 ta ulanish yetarli
    pool_size=3,
    max_overflow=5,
    pool_recycle=1800,       # 30 daqiqada bir yangilansin
    pool_timeout=15,
    pool_pre_ping=True,      # Har ulanish tekshirilsin
    connect_args={
        "command_timeout": 10,
        "server_settings": {
            "statement_timeout":    "15000",  # 15 sek max
            "lock_timeout":         "5000",   # 5 sek lock kutish
            "idle_in_transaction_session_timeout": "30000",  # 30 sek
        }
    }
)

# ──────────────────────────────────────────────
# SESSION FACTORY
# ──────────────────────────────────────────────
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # commit'dan keyin ob'ektlar qayta yuklanmasin
    autoflush=False,           # Manuel flush uchun
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (dependency injection uchun)"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database — barcha jadvallarni yaratish"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise


async def close_db():
    """Close all database connections gracefully"""
    await engine.dispose()
    logger.info("Database connections closed")
