"""
Database module for AvatarFactory.

This module provides SQLAlchemy-based database support with:
- SQLite as the default database (zero-configuration)
- Optional PostgreSQL support via AVATARFACTORY_DB_URL environment variable
- Repository pattern for data access abstraction
"""

from avatarfactory.core.database.connection import (
    get_engine,
    get_session,
    init_database,
    AsyncSessionLocal,
)
from avatarfactory.core.database.models import Base

__all__ = [
    "get_engine",
    "get_session",
    "init_database",
    "AsyncSessionLocal",
    "Base",
]
