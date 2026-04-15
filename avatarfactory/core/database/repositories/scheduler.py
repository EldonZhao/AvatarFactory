"""
Scheduler repository for database operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, delete

from avatarfactory.core.database.models import (
    ScheduledTaskModel,
    PublishQueueModel,
    TrendSnapshotModel,
    RecommendedPersonaModel,
)
from avatarfactory.core.database.repositories.base import BaseRepository


class SchedulerRepository(BaseRepository[ScheduledTaskModel]):
    """Repository for ScheduledTask CRUD and queries."""

    model = ScheduledTaskModel

    async def list_all(self) -> List[ScheduledTaskModel]:
        """
        List all tasks.

        Returns:
            List of all ScheduledTaskModel instances
        """
        query = (
            select(ScheduledTaskModel)
            .order_by(ScheduledTaskModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

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

    async def list_system_tasks(self) -> List[ScheduledTaskModel]:
        """
        List system-level tasks (no persona association).

        Returns:
            List of ScheduledTaskModel instances
        """
        query = (
            select(ScheduledTaskModel)
            .where(ScheduledTaskModel.persona_id.is_(None))
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

    async def update_task(
        self,
        task_id: str,
        updates: Dict[str, Any],
    ) -> Optional[ScheduledTaskModel]:
        """
        Update task properties.

        Args:
            task_id: Task ID
            updates: Dictionary of fields to update

        Returns:
            Updated ScheduledTaskModel or None if not found
        """
        task = await self.get(task_id)
        if not task:
            return None

        allowed_fields = {"name", "schedule", "platform", "enabled", "extra_params"}
        for field, value in updates.items():
            if field in allowed_fields and hasattr(task, field):
                setattr(task, field, value)

        task.updated_at = datetime.utcnow()
        await self.session.flush()
        return task

    async def delete_by_persona(self, persona_id: str) -> int:
        """
        Delete all tasks for a specific persona.

        Args:
            persona_id: Persona ID

        Returns:
            Number of tasks deleted
        """
        query = (
            delete(ScheduledTaskModel)
            .where(ScheduledTaskModel.persona_id == persona_id)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount or 0

    async def create_task(
        self,
        task_id: str,
        name: str,
        task_type: str,
        schedule: str,
        enabled: bool = True,
        persona_id: Optional[str] = None,
        platform: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTaskModel:
        """
        Create a new scheduled task.

        Args:
            task_id: Unique task ID
            name: Task name
            task_type: Task type
            schedule: Cron expression
            enabled: Whether task is enabled
            persona_id: Optional persona association
            platform: Optional platform
            extra_params: Optional extra parameters

        Returns:
            Created ScheduledTaskModel
        """
        task = ScheduledTaskModel(
            id=task_id,
            name=name,
            task_type=task_type,
            schedule=schedule,
            enabled=enabled,
            persona_id=persona_id,
            platform=platform,
            extra_params=extra_params or {},
            run_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def upsert_task(
        self,
        task_id: str,
        name: str,
        task_type: str,
        schedule: str,
        enabled: bool = True,
        persona_id: Optional[str] = None,
        platform: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTaskModel:
        """
        Create or update a scheduled task.

        Args:
            task_id: Unique task ID
            name: Task name
            task_type: Task type
            schedule: Cron expression
            enabled: Whether task is enabled
            persona_id: Optional persona association
            platform: Optional platform
            extra_params: Optional extra parameters

        Returns:
            Created or updated ScheduledTaskModel
        """
        existing = await self.get(task_id)
        if existing:
            existing.name = name
            existing.task_type = task_type
            existing.schedule = schedule
            existing.enabled = enabled
            existing.persona_id = persona_id
            existing.platform = platform
            existing.extra_params = extra_params or {}
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            return existing
        else:
            return await self.create_task(
                task_id=task_id,
                name=name,
                task_type=task_type,
                schedule=schedule,
                enabled=enabled,
                persona_id=persona_id,
                platform=platform,
                extra_params=extra_params,
            )


class PublishQueueRepository(BaseRepository[PublishQueueModel]):
    """Repository for PublishQueue CRUD and queries."""

    model = PublishQueueModel

    async def list_pending(
        self,
        scheduled_before: Optional[datetime] = None,
    ) -> List[PublishQueueModel]:
        """
        List pending items ready to publish.

        Args:
            scheduled_before: Only include items scheduled before this time

        Returns:
            List of pending PublishQueueModel instances
        """
        conditions = [PublishQueueModel.status == "pending"]
        if scheduled_before:
            conditions.append(
                (PublishQueueModel.scheduled_time.is_(None)) |
                (PublishQueueModel.scheduled_time <= scheduled_before)
            )

        query = (
            select(PublishQueueModel)
            .where(and_(*conditions))
            .order_by(PublishQueueModel.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> List[PublishQueueModel]:
        """
        List items by status.

        Args:
            status: Status filter ('pending', 'published', 'failed')

        Returns:
            List of PublishQueueModel instances
        """
        query = (
            select(PublishQueueModel)
            .where(PublishQueueModel.status == status)
            .order_by(PublishQueueModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_published(
        self,
        item_id: str,
        post_url: Optional[str] = None,
    ) -> bool:
        """
        Mark an item as published.

        Args:
            item_id: Queue item ID
            post_url: URL of the published post

        Returns:
            True if updated, False if not found
        """
        item = await self.get(item_id)
        if item:
            item.status = "published"
            item.published_at = datetime.utcnow()
            item.post_url = post_url
            await self.session.flush()
            return True
        return False

    async def mark_failed(
        self,
        item_id: str,
        error: str,
    ) -> bool:
        """
        Mark an item as failed.

        Args:
            item_id: Queue item ID
            error: Error message

        Returns:
            True if updated, False if not found
        """
        item = await self.get(item_id)
        if item:
            item.status = "failed"
            item.error = error
            await self.session.flush()
            return True
        return False

    async def create_item(
        self,
        item_id: str,
        content_id: str,
        platform: str,
        scheduled_time: Optional[datetime] = None,
    ) -> PublishQueueModel:
        """
        Create a new publish queue item.

        Args:
            item_id: Unique item ID
            content_id: Content ID to publish
            platform: Target platform
            scheduled_time: Optional scheduled time

        Returns:
            Created PublishQueueModel
        """
        item = PublishQueueModel(
            id=item_id,
            content_id=content_id,
            platform=platform,
            scheduled_time=scheduled_time,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.session.add(item)
        await self.session.flush()
        return item


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
