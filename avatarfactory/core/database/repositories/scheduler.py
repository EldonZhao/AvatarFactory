"""
Scheduler repository for database operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_

from avatarfactory.core.database.models import (
    ScheduledTaskModel,
    TrendSnapshotModel,
    RecommendedPersonaModel,
)
from avatarfactory.core.database.repositories.base import BaseRepository


class SchedulerRepository(BaseRepository[ScheduledTaskModel]):
    """Repository for ScheduledTask CRUD and queries."""

    model = ScheduledTaskModel

    async def list_enabled(self) -> List[ScheduledTaskModel]:
        """
        List all enabled tasks.

        Returns:
            List of enabled ScheduledTaskModel instances
        """
        query = (
            select(ScheduledTaskModel)
            .where(ScheduledTaskModel.enabled == True)  # noqa: E712
            .order_by(ScheduledTaskModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_persona(self, persona_id: str) -> List[ScheduledTaskModel]:
        """
        List tasks for a specific persona.

        Args:
            persona_id: Persona ID

        Returns:
            List of ScheduledTaskModel instances
        """
        query = (
            select(ScheduledTaskModel)
            .where(ScheduledTaskModel.persona_id == persona_id)
            .order_by(ScheduledTaskModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_type(self, task_type: str) -> List[ScheduledTaskModel]:
        """
        List tasks by type.

        Args:
            task_type: Task type (e.g., 'topic', 'content', 'trend_scan')

        Returns:
            List of ScheduledTaskModel instances
        """
        query = (
            select(ScheduledTaskModel)
            .where(ScheduledTaskModel.task_type == task_type)
            .order_by(ScheduledTaskModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_platform(
        self,
        platform: str,
        task_type: str,
    ) -> Optional[ScheduledTaskModel]:
        """
        Get task by platform and type.

        Args:
            platform: Platform name
            task_type: Task type

        Returns:
            ScheduledTaskModel or None
        """
        query = select(ScheduledTaskModel).where(
            and_(
                ScheduledTaskModel.platform == platform,
                ScheduledTaskModel.task_type == task_type,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_run_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update task run status.

        Args:
            task_id: Task ID
            status: New status ('success', 'error')
            error: Error message if status is 'error'

        Returns:
            True if updated, False if task not found
        """
        task = await self.get(task_id)
        if task:
            task.last_run = datetime.utcnow()
            task.last_status = status
            task.last_error = error
            task.run_count += 1
            task.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def toggle_enabled(self, task_id: str, enabled: bool) -> bool:
        """
        Enable or disable a task.

        Args:
            task_id: Task ID
            enabled: New enabled state

        Returns:
            True if updated, False if task not found
        """
        task = await self.get(task_id)
        if task:
            task.enabled = enabled
            task.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False


class TrendSnapshotRepository(BaseRepository[TrendSnapshotModel]):
    """Repository for TrendSnapshot CRUD and queries."""

    model = TrendSnapshotModel

    async def list_by_platform(
        self,
        platform: str,
        limit: int = 10,
    ) -> List[TrendSnapshotModel]:
        """
        List trend snapshots for a platform.

        Args:
            platform: Platform name
            limit: Maximum results

        Returns:
            List of TrendSnapshotModel instances (newest first)
        """
        query = (
            select(TrendSnapshotModel)
            .where(TrendSnapshotModel.platform == platform)
            .order_by(TrendSnapshotModel.captured_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, platform: str) -> Optional[TrendSnapshotModel]:
        """
        Get the latest trend snapshot for a platform.

        Args:
            platform: Platform name

        Returns:
            Latest TrendSnapshotModel or None
        """
        query = (
            select(TrendSnapshotModel)
            .where(TrendSnapshotModel.platform == platform)
            .order_by(TrendSnapshotModel.captured_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class RecommendedPersonaRepository(BaseRepository[RecommendedPersonaModel]):
    """Repository for RecommendedPersona CRUD and queries."""

    model = RecommendedPersonaModel

    async def list_active(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RecommendedPersonaModel]:
        """
        List active (non-adopted) recommendations.

        Args:
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of RecommendedPersonaModel instances
        """
        query = (
            select(RecommendedPersonaModel)
            .where(RecommendedPersonaModel.status == "active")
            .order_by(RecommendedPersonaModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_adopted(
        self,
        recommendation_id: str,
        persona_id: str,
    ) -> bool:
        """
        Mark a recommendation as adopted.

        Args:
            recommendation_id: Recommendation ID
            persona_id: ID of the created persona

        Returns:
            True if updated, False if not found
        """
        rec = await self.get(recommendation_id)
        if rec:
            rec.status = "adopted"
            rec.adopted_persona_id = persona_id
            await self.session.flush()
            return True
        return False

    async def dismiss(self, recommendation_id: str) -> bool:
        """
        Dismiss a recommendation.

        Args:
            recommendation_id: Recommendation ID

        Returns:
            True if updated, False if not found
        """
        rec = await self.get(recommendation_id)
        if rec:
            rec.status = "dismissed"
            await self.session.flush()
            return True
        return False
