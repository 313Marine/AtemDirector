"""Database configuration and session management."""
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
import os

from atem_director.logging import get_logger
from atem_director.persistence.models import Base

logger = get_logger(__name__)

# Global engine and session factory
_engine: Optional[any] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db(database_url: Optional[str] = None) -> None:
    """Initialize database connection.
    
    Args:
        database_url: Database connection URL. If None, uses SQLite in local directory.
    """
    global _engine, _session_factory
    
    # Default to SQLite if no URL provided
    if database_url is None:
        db_path = os.path.join(
            os.path.expanduser("~"),
            ".atem_director",
            "atem_director.db"
        )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        database_url = f"sqlite+aiosqlite:///{db_path}"
        logger.info("Using SQLite database", path=db_path)
    
    logger.info("Initializing database", url=database_url.split("@")[1] if "@" in database_url else database_url)
    
    _engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        future=True,
        # SQLite-specific settings
        connect_args={"timeout": 30} if "sqlite" in database_url else {},
    )
    
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized and tables created")


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

