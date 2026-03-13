"""Database configuration and session management."""
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from atem_director.logging import get_logger

logger = get_logger(__name__)

# Global engine and session factory
_engine: Optional[any] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db(database_url: str) -> None:
    """Initialize database connection.
    
    Args:
        database_url: Database connection URL
    """
    global _engine, _session_factory
    
    logger.info("Initializing database", url=database_url.split("@")[1] if "@" in database_url else "***")
    
    _engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        future=True,
    )
    
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    logger.info("Database initialized")


async def close_db() -> None:
    """Close database connection."""
    global _engine
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection closed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.
    
    Yields:
        AsyncSession instance
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    
    async with _session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
