"""
Base repository class with common CRUD operations.
"""

from abc import ABC
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from avatarfactory.core.database.models import Base

T = TypeVar("T", bound=Base)


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common CRUD operations.

    Subclasses should specify the model class and can override
    or extend methods as needed.
    """

    model: Type[T]

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with a database session.

        Args:
            session: AsyncSession instance
        """
        self.session = session

    async def get(self, id: str) -> Optional[T]:
        """
        Get a single entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        return await self.session.get(self.model, id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        **filters: Any,
    ) -> List[T]:
        """
        List entities with optional filtering and pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Column name to order by (prefix with - for descending)
            **filters: Filter conditions as column=value pairs

        Returns:
            List of entity instances
        """
        query = select(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                column = getattr(self.model, key)
                if value is not None:
                    query = query.where(column == value)

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                column = getattr(self.model, order_by[1:], None)
                if column is not None:
                    query = query.order_by(column.desc())
            else:
                column = getattr(self.model, order_by, None)
                if column is not None:
                    query = query.order_by(column.asc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def save(self, entity: T) -> T:
        """
        Save (insert or update) an entity.

        Args:
            entity: Entity instance to save

        Returns:
            Saved entity instance
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: str) -> bool:
        """
        Delete an entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if entity was deleted, False if not found
        """
        entity = await self.get(id)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()
            return True
        return False

    async def count(self, **filters: Any) -> int:
        """
        Count entities with optional filtering.

        Args:
            **filters: Filter conditions as column=value pairs

        Returns:
            Number of matching entities
        """
        query = select(func.count()).select_from(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key):
                column = getattr(self.model, key)
                if value is not None:
                    query = query.where(column == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, id: str) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            id: Entity ID

        Returns:
            True if entity exists, False otherwise
        """
        entity = await self.get(id)
        return entity is not None

    async def bulk_save(self, entities: List[T]) -> List[T]:
        """
        Save multiple entities at once.

        Args:
            entities: List of entity instances

        Returns:
            List of saved entity instances
        """
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def bulk_delete(self, ids: List[str]) -> int:
        """
        Delete multiple entities by IDs.

        Args:
            ids: List of entity IDs

        Returns:
            Number of deleted entities
        """
        # Get primary key column
        pk_column = list(self.model.__table__.primary_key.columns)[0]

        stmt = delete(self.model).where(pk_column.in_(ids))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
