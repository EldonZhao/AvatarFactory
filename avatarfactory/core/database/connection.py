"""
Database connection management for AvatarFactory.

Supports both SQLite (default) and PostgreSQL via environment variable.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url(kb_path: str = "./knowledges") -> str:
    """
    Get the database URL from environment or default to SQLite.

    Priority:
    1. AVATARFACTORY_DB_URL environment variable
    2. SQLite file in knowledges directory
    """
    db_url = os.getenv("AVATARFACTORY_DB_URL")
    if db_url:
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return db_url

    # Default to SQLite in knowledges directory
    db_path = Path(kb_path) / "avatarfactory.db"
    return f"sqlite+aiosqlite:///{db_path.absolute()}"


def get_engine(db_url: Optional[str] = None, kb_path: str = "./knowledges") -> AsyncEngine:
    """
    Get or create the database engine.

    Args:
        db_url: Optional explicit database URL
        kb_path: Path to knowledges directory (used for default SQLite location)

    Returns:
        AsyncEngine instance

    Environment variables for tuning:
        AVATARFACTORY_DB_ECHO: Set to "true" for SQL logging
        AVATARFACTORY_DB_POOL_SIZE: Connection pool size (PostgreSQL, default: 5)
        AVATARFACTORY_DB_MAX_OVERFLOW: Max overflow connections (PostgreSQL, default: 10)
        AVATARFACTORY_DB_POOL_TIMEOUT: Pool checkout timeout in seconds (default: 30)
        AVATARFACTORY_DB_POOL_RECYCLE: Connection recycle time in seconds (default: 1800)
    """
    global _engine

    if _engine is None:
        url = db_url or get_database_url(kb_path)
        echo = os.getenv("AVATARFACTORY_DB_ECHO", "").lower() == "true"

        # Configure engine based on database type
        if "sqlite" in url:
            _engine = create_async_engine(
                url,
                echo=echo,
                # SQLite specific settings for better concurrency
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,  # Busy timeout in seconds
                },
                # Use StaticPool for SQLite to share connection across threads
                poolclass=StaticPool,
            )
        else:
            # PostgreSQL with connection pooling
            pool_size = int(os.getenv("AVATARFACTORY_DB_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("AVATARFACTORY_DB_MAX_OVERFLOW", "10"))
            pool_timeout = int(os.getenv("AVATARFACTORY_DB_POOL_TIMEOUT", "30"))
            pool_recycle = int(os.getenv("AVATARFACTORY_DB_POOL_RECYCLE", "1800"))

            _engine = create_async_engine(
                url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # Enable connection health check
            )

    return _engine


def get_session_factory(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the session factory.

    Args:
        engine: Optional AsyncEngine instance

    Returns:
        async_sessionmaker instance
    """
    global _session_factory

    if _session_factory is None:
        eng = engine or get_engine()
        _session_factory = async_sessionmaker(
            eng,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _session_factory


# Alias for convenience
def AsyncSessionLocal() -> async_sessionmaker[AsyncSession]:
    """Get the async session factory."""
    return get_session_factory()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_database(
    db_url: Optional[str] = None,
    kb_path: str = "./knowledges",
    drop_existing: bool = False,
) -> None:
    """
    Initialize the database schema.

    Args:
        db_url: Optional explicit database URL
        kb_path: Path to knowledges directory
        drop_existing: If True, drop existing tables first (DANGEROUS)
    """
    from avatarfactory.core.database.models import Base

    engine = get_engine(db_url, kb_path)

    # Ensure the knowledges directory exists for SQLite
    if "sqlite" in str(engine.url):
        db_path = Path(kb_path)
        db_path.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        if drop_existing:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close the database connection."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def reset_engine() -> None:
    """
    Reset the global engine (useful for testing).
    """
    global _engine, _session_factory
    _engine = None
    _session_factory = None
