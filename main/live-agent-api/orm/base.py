"""
ORM Base Infrastructure

Database configuration and utilities for SQLAlchemy ORM.
Provides the declarative base, engine management, and session handling.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base

from config.settings import settings

logger = logging.getLogger(__name__)

# SQLAlchemy declarative base for all ORM models
Base = declarative_base()

# Global instances
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global async database engine
    
    Returns:
        Async SQLAlchemy engine instance
    """
    global _engine
    
    if _engine is None:
        logger.info("Creating database engine")
        _engine = create_async_engine(
            str(settings.database_url),
            echo=settings.app_env == "development",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the global async session maker
    
    Returns:
        Async session maker instance
    """
    global _async_session_maker
    
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency function to get database session
    
    Yields:
        Async database session
        
    Example:
        ```python
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize database tables
    
    Creates all tables defined in SQLAlchemy models.
    Should be called once during application startup in lifespan.
    """
    engine = get_engine()
    
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # Import all models to ensure they are registered with Base
        from orm.agent import Agent  # noqa: F401
        # Future: from orm.device import Device
        # Future: from orm.binding import Binding
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables initialized successfully")


async def close_database() -> None:
    """
    Close database connections
    
    Should be called during application shutdown in lifespan.
    """
    global _engine
    
    if _engine is not None:
        logger.info("Closing database connections...")
        await _engine.dispose()
        _engine = None
        logger.info("Database connections closed")

