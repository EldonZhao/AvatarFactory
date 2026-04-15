"""
Scheduler Engine for AvatarFactory.

Provides task scheduling using APScheduler with database persistence and management.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

# Suppress tzlocal timezone offset warning (common on Windows)
warnings.filterwarnings("ignore", message="Timezone offset does not match system offset")

logger = logging.getLogger("avatarfactory.scheduler")


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    # Legacy data directory for migration
    data_dir: str = Field(
        default_factory=lambda: os.path.join(
            os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"), "scheduler"
        )
    )

    # Default schedules (cron expressions)
    discovery_schedule: str = Field(
        default="0 9 * * *",  # Daily at 9 AM
        description="Cron schedule for discovery tasks"
    )
    content_schedule: str = Field(
        default="0 10 * * *",  # Daily at 10 AM
        description="Cron schedule for content generation"
    )
    publish_schedule: str = Field(
        default="0 12,18 * * *",  # Twice daily at 12 PM and 6 PM
        description="Cron schedule for publishing queued content"
    )
    weekly_report_schedule: str = Field(
        default="0 18 * * 5",  # Friday at 6 PM
        description="Cron schedule for weekly reports"
    )

    # Behavior
    max_retries: int = Field(default=3)
    retry_delay_seconds: int = Field(default=60)


class ScheduledTask(BaseModel):
    """A scheduled task definition."""

    id: str
    name: str
    task_type: str  # discovery, content, publish, report
    schedule: str  # cron expression
    enabled: bool = True

    # Task parameters
    persona_id: Optional[str] = None
    platform: Optional[str] = None
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    # Status
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int = 0


class PublishQueueItem(BaseModel):
    """Item in the publish queue."""

    id: str
    content_id: str
    platform: str
    scheduled_time: Optional[datetime] = None
    status: str = "pending"  # pending, published, failed
    created_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    error: Optional[str] = None
    post_url: Optional[str] = None


class Scheduler:
    """
    Main scheduler class for AvatarFactory.

    Uses database storage for tasks and publish queue.
    APScheduler handles the actual scheduling in memory.

    Manages background tasks for:
    - Periodic discovery and trend analysis
    - Automated content generation
    - Scheduled publishing
    - Weekly reports and notifications
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self._scheduler = None
        self._running = False
        self._tasks: Dict[str, ScheduledTask] = {}  # In-memory cache
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Legacy data directory for migration check
        self._data_dir = Path(self.config.data_dir)

    async def _load_tasks_from_db(self) -> None:
        """Load all tasks from database into memory cache."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        try:
            async with get_session() as session:
                repo = SchedulerRepository(session)
                db_tasks = await repo.list_all()

                self._tasks.clear()
                for db_task in db_tasks:
                    task = ScheduledTask(
                        id=db_task.id,
                        name=db_task.name,
                        task_type=db_task.task_type,
                        schedule=db_task.schedule,
                        enabled=db_task.enabled,
                        persona_id=db_task.persona_id,
                        platform=db_task.platform,
                        extra_params=db_task.extra_params or {},
                        last_run=db_task.last_run,
                        last_status=db_task.last_status,
                        last_error=db_task.last_error,
                        run_count=db_task.run_count or 0,
                    )
                    self._tasks[task.id] = task

                logger.info(f"Loaded {len(self._tasks)} tasks from database")

        except Exception as e:
            logger.warning(f"Failed to load tasks from database: {e}")
            # Fall back to JSON if database is not initialized
            self._load_tasks_from_json()

    def _load_tasks_from_json(self) -> None:
        """Legacy: Load tasks from JSON file (for migration)."""
        tasks_file = self._data_dir / "tasks.json"

        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = ScheduledTask(**task_data)
                        self._tasks[task.id] = task
                logger.info(f"Loaded {len(self._tasks)} tasks from JSON (legacy)")
            except Exception as e:
                logger.warning(f"Failed to load tasks from JSON: {e}")

    async def _ensure_system_tasks(self) -> None:
        """
        Ensure system-level scheduled tasks exist in database.

        These are global tasks that don't require a persona:
        - trend_scan: Daily scan of trending topics across platforms
        - persona_recommendation: Daily persona recommendations based on trends
        """
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        system_tasks = [
            {
                "task_id": "system_trend_scan",
                "name": "Daily Trend Scan",
                "task_type": "trend_scan",
                "schedule": "0 8 * * *",  # Daily at 8 AM
                "enabled": True,
                "persona_id": None,
                "platform": None,
                "extra_params": {"platforms": ["bluesky"]},
            },
            {
                "task_id": "system_persona_recommendation",
                "name": "Daily Persona Recommendation",
                "task_type": "persona_recommendation",
                "schedule": "0 9 * * *",  # Daily at 9 AM (1 hour after trend scan)
                "enabled": True,
                "persona_id": None,
                "platform": None,
                "extra_params": {"count": 3},
            },
        ]

        try:
            async with get_session() as session:
                repo = SchedulerRepository(session)

                for task_dict in system_tasks:
                    task_id = task_dict["task_id"]
                    existing = await repo.get(task_id)
                    if not existing:
                        await repo.create_task(**task_dict)
                        logger.info(f"Created system task: {task_dict['name']}")

                        # Also add to memory cache
                        task = ScheduledTask(
                            id=task_id,
                            name=task_dict["name"],
                            task_type=task_dict["task_type"],
                            schedule=task_dict["schedule"],
                            enabled=task_dict["enabled"],
                            persona_id=task_dict["persona_id"],
                            platform=task_dict["platform"],
                            extra_params=task_dict["extra_params"],
                        )
                        self._tasks[task_id] = task

        except Exception as e:
            logger.warning(f"Failed to ensure system tasks: {e}")

    async def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task to database and memory."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        async with get_session() as session:
            repo = SchedulerRepository(session)
            await repo.upsert_task(
                task_id=task.id,
                name=task.name,
                task_type=task.task_type,
                schedule=task.schedule,
                enabled=task.enabled,
                persona_id=task.persona_id,
                platform=task.platform,
                extra_params=task.extra_params,
            )

        # Update memory cache
        self._tasks[task.id] = task

        if self._running and self._scheduler:
            self._schedule_task(task)

    def add_task_sync(self, task: ScheduledTask) -> None:
        """Synchronous wrapper for add_task."""
        asyncio.get_event_loop().run_until_complete(self.add_task(task))

    async def add_task_from_dict(self, task_dict: Dict[str, Any]) -> ScheduledTask:
        """
        Add a scheduled task from a dictionary.

        Args:
            task_dict: Dictionary with task properties

        Returns:
            The created ScheduledTask
        """
        task = ScheduledTask(**task_dict)
        await self.add_task(task)
        return task

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[ScheduledTask]:
        """
        Update a scheduled task's properties.

        Args:
            task_id: The task ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated ScheduledTask or None if not found
        """
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        if task_id not in self._tasks:
            return None

        task = self._tasks[task_id]
        schedule_changed = False

        # Update allowed fields
        allowed_fields = {"name", "schedule", "platform", "enabled", "extra_params"}
        for field, value in updates.items():
            if field in allowed_fields and hasattr(task, field):
                if field == "schedule" and getattr(task, field) != value:
                    schedule_changed = True
                setattr(task, field, value)

        # Persist to database
        async with get_session() as session:
            repo = SchedulerRepository(session)
            await repo.update_task(task_id, updates)

        # Reschedule if running and schedule changed or enabled state changed
        if self._running and self._scheduler:
            if schedule_changed or "enabled" in updates:
                try:
                    self._scheduler.remove_job(task_id)
                except Exception:
                    pass
                if task.enabled:
                    self._schedule_task(task)

        return task

    async def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        if task_id not in self._tasks:
            return False

        # Remove from database
        async with get_session() as session:
            repo = SchedulerRepository(session)
            await repo.delete(task_id)

        # Remove from memory cache
        del self._tasks[task_id]

        # Remove from APScheduler if running
        if self._running and self._scheduler:
            try:
                self._scheduler.remove_job(task_id)
            except Exception:
                pass

        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID from memory cache."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks from memory cache."""
        return list(self._tasks.values())

    async def remove_tasks_for_persona(self, persona_id: str) -> int:
        """Remove all scheduled tasks for a specific persona."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        tasks_to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.persona_id == persona_id
        ]

        # Remove from database
        async with get_session() as session:
            repo = SchedulerRepository(session)
            await repo.delete_by_persona(persona_id)

        # Remove from memory and APScheduler
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
            if self._running and self._scheduler:
                try:
                    self._scheduler.remove_job(task_id)
                except Exception:
                    pass

        return len(tasks_to_remove)

    async def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        if task_id not in self._tasks:
            return False

        self._tasks[task_id].enabled = True

        async with get_session() as session:
            repo = SchedulerRepository(session)
            await repo.toggle_enabled(task_id, True)

        return True

    async def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        if task_id not in self._tasks:
            return False

        self._tasks[task_id].enabled = False

        async with get_session() as session:
            repo = SchedulerRepository(session)
            await repo.toggle_enabled(task_id, False)

        return True

    # =========================================================================
    # Publish Queue
    # =========================================================================

    async def queue_publish(
        self,
        content_id: str,
        platform: str,
        scheduled_time: Optional[datetime] = None,
    ) -> PublishQueueItem:
        """Add content to the publish queue."""
        import uuid
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import PublishQueueRepository

        item_id = f"pub_{uuid.uuid4().hex[:8]}"
        item = PublishQueueItem(
            id=item_id,
            content_id=content_id,
            platform=platform,
            scheduled_time=scheduled_time,
        )

        async with get_session() as session:
            repo = PublishQueueRepository(session)
            await repo.create_item(
                item_id=item_id,
                content_id=content_id,
                platform=platform,
                scheduled_time=scheduled_time,
            )

        return item

    async def get_publish_queue(self, status: Optional[str] = None) -> List[PublishQueueItem]:
        """Get publish queue items."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import PublishQueueRepository

        async with get_session() as session:
            repo = PublishQueueRepository(session)
            if status:
                db_items = await repo.list_by_status(status)
            else:
                db_items = await repo.list_pending()

        items = []
        for db_item in db_items:
            items.append(PublishQueueItem(
                id=db_item.id,
                content_id=db_item.content_id,
                platform=db_item.platform,
                scheduled_time=db_item.scheduled_time,
                status=db_item.status,
                created_at=db_item.created_at,
                published_at=db_item.published_at,
                error=db_item.error,
                post_url=db_item.post_url,
            ))
        return items

    async def remove_from_queue(self, item_id: str) -> bool:
        """Remove item from publish queue."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import PublishQueueRepository

        async with get_session() as session:
            repo = PublishQueueRepository(session)
            return await repo.delete(item_id)

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit(self, event: str, data: Any) -> None:
        """Emit an event to handlers."""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    # =========================================================================
    # Scheduler Control
    # =========================================================================

    def _schedule_task(self, task: ScheduledTask) -> None:
        """Schedule a single task with APScheduler."""
        if not task.enabled:
            return

        from apscheduler.triggers.cron import CronTrigger

        try:
            # Parse cron expression
            parts = task.schedule.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                )
            else:
                logger.warning(f"Invalid cron expression for task {task.id}: {task.schedule}")
                return

            # Add job
            self._scheduler.add_job(
                self._run_task,
                trigger=trigger,
                id=task.id,
                args=[task.id],
                replace_existing=True,
            )
            logger.info(f"Scheduled task: {task.name} ({task.schedule})")

        except Exception as e:
            logger.error(f"Failed to schedule task {task.id}: {e}")

    def _run_task(self, task_id: str) -> None:
        """Execute a scheduled task (synchronous wrapper)."""
        import asyncio

        # Run the async task in a new event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_task_async(task_id))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error running task {task_id}: {e}")

    async def _run_task_async(self, task_id: str) -> None:
        """Execute a scheduled task."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

        task = self._tasks.get(task_id)
        if not task or not task.enabled:
            return

        logger.info(f"Running task: {task.name}")
        task.last_run = datetime.now()
        task.run_count += 1

        try:
            # Import task runners
            from avatarfactory.scheduler.tasks import TaskRegistry

            runner = TaskRegistry.get_runner(task.task_type)
            if runner:
                result = await runner(task)
                task.last_status = "success"
                task.last_error = None
                self._emit("task_completed", {"task": task, "result": result})

                # Send notification
                await self._notify_task_completed(task, result)
            else:
                task.last_status = "error"
                task.last_error = f"Unknown task type: {task.task_type}"

        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
            task.last_status = "error"
            task.last_error = str(e)
            self._emit("task_failed", {"task": task, "error": str(e)})

            # Send error notification
            await self._notify_task_failed(task, str(e))

        # Update database with run status
        try:
            async with get_session() as session:
                repo = SchedulerRepository(session)
                await repo.update_run_status(
                    task_id,
                    task.last_status or "unknown",
                    task.last_error,
                )
        except Exception as e:
            logger.warning(f"Failed to update task status in database: {e}")

    async def _notify_task_completed(self, task: ScheduledTask, result: Dict[str, Any]) -> None:
        """
        Send notification when task completes.

        Notification strategy:
        - discovery: Send markdown format report (trending topics, ideas)
        - content: Send news card format with link to content
        - Other types: Console only, no webhook notification
        """
        import os
        from avatarfactory.notifications import ConsoleNotifier, NotificationMessage, NotificationPriority

        # Build console notification for all task types
        if task.task_type in ("topic", "discovery"):
            title = f"Discovery Complete: {task.name}"
            body = f"Found {result.get('trending_count', 0)} trending posts, generated {result.get('ideas_count', 0)} ideas."
            if result.get('suggestions'):
                body += f"\nSuggestions: {result['suggestions'][0][:100]}..."
        elif task.task_type == "content":
            title = f"Content Generated: {task.name}"
            body = f"Created: {result.get('title', 'New content')}\nID: {result.get('content_id', 'N/A')}"
        elif task.task_type == "report":
            title = f"Report Ready: {task.name}"
            report = result.get('report', {})
            stats = report.get('stats', {})
            body = f"Published: {stats.get('total_published', 0)}, Drafts: {stats.get('total_drafts', 0)}"
        else:
            title = f"Task Complete: {task.name}"
            body = f"Result: {result}"

        message = NotificationMessage(
            title=title,
            body=body,
            priority=NotificationPriority.NORMAL,
            category="task_completed",
        )

        # Send to console for all task types
        console_notifier = ConsoleNotifier()
        await console_notifier.send(message)

        # Send to webhook only for discovery and content tasks
        webhook_url = os.getenv("AVATARFACTORY_WEBHOOK_URL")
        if not webhook_url:
            return

        # Check if persona has notifications enabled
        if task.persona_id:
            from avatarfactory.core.knowledges_db import get_knowledge_base
            kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
            kb = get_knowledge_base(kb_path)
            persona = kb.load_persona(task.persona_id)
            if persona:
                # Check if persona has notification disabled
                if persona.notification is None or not persona.notification.enabled:
                    logger.debug(f"Skipping notification for persona {task.persona_id}: notifications disabled")
                    return

                # Check notification type preferences
                if task.task_type in ("topic", "discovery") and not persona.notification.notify_on_discovery:
                    logger.debug(f"Skipping topic notification for persona {task.persona_id}")
                    return
                if task.task_type == "content" and not persona.notification.notify_on_content:
                    logger.debug(f"Skipping content notification for persona {task.persona_id}")
                    return

        # Only send webhook notifications for discovery and content tasks
        if task.task_type in ("topic", "discovery"):
            # Discovery: Use markdown format for detailed report
            await self._send_topic_webhook_notification(task, result, webhook_url)
        elif task.task_type == "content":
            # Content: Use news card format with link
            await self._send_content_webhook_notification(task, result, webhook_url)

    async def _send_topic_webhook_notification(
        self, task: ScheduledTask, result: Dict[str, Any], webhook_url: str
    ) -> None:
        """Send topic task notification using markdown format."""
        import httpx

        # Build markdown content
        parts = []
        parts.append(f"### 🔍 {task.name}")
        parts.append("")

        # Trending count and ideas count
        trending_count = result.get('trending_count', 0)
        ideas_count = result.get('ideas_count', 0)
        parts.append(f"📊 发现 **{trending_count}** 条热点，生成 **{ideas_count}** 个创意")
        parts.append("")

        # Pattern analysis
        pattern_analysis = result.get('pattern_analysis', {})
        if pattern_analysis:
            trending_topics = pattern_analysis.get('trending_topics', [])
            if trending_topics:
                parts.append("**🔥 热点话题:**")
                for topic in trending_topics[:5]:
                    parts.append(f"> {topic}")
                parts.append("")

            key_insights = pattern_analysis.get('key_insights', [])
            if key_insights:
                parts.append("**💡 关键洞察:**")
                for insight in key_insights[:3]:
                    parts.append(f"> {insight}")
                parts.append("")

        # Ideas/suggestions
        ideas = result.get('ideas', [])
        suggestions = result.get('suggestions', [])
        if ideas:
            parts.append("**📝 创作建议:**")
            for idea in ideas[:3]:
                topic = idea.get('topic', '') if isinstance(idea, dict) else str(idea)
                parts.append(f"> {topic}")
            parts.append("")
        elif suggestions:
            parts.append("**📝 创作建议:**")
            for suggestion in suggestions[:3]:
                parts.append(f"> {suggestion[:100]}...")
            parts.append("")

        content = "\n".join(parts)

        # Send via WeChat Work markdown format
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        logger.info(f"Sent topic notification for task {task.id}")
                    else:
                        logger.warning(f"Topic notification failed: {data.get('errmsg')}")
                else:
                    logger.warning(f"Topic notification HTTP error: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to send topic notification: {e}")

    async def _send_content_webhook_notification(
        self, task: ScheduledTask, result: Dict[str, Any], webhook_url: str
    ) -> None:
        """Send content task notification using news card format."""
        import os
        import httpx

        content_id = result.get('content_id', '')
        content_title = result.get('title', 'New Content')
        content_body = result.get('body', '')
        review_score = result.get('review_score')
        persona_name = result.get('persona_name', '')
        platform = result.get('platform', '')

        # Build description
        description_parts = []
        if persona_name:
            description_parts.append(f"👤 {persona_name}")
        if platform:
            description_parts.append(f"📱 {platform}")
        if review_score is not None:
            if review_score >= 80:
                description_parts.append(f"✅ 评分: {review_score:.0f}/100")
            elif review_score >= 60:
                description_parts.append(f"⚠️ 评分: {review_score:.0f}/100")
            else:
                description_parts.append(f"❌ 评分: {review_score:.0f}/100")

        # Content preview
        body_preview = content_body[:300] if content_body else ''
        if len(content_body) > 300:
            body_preview += "..."

        if description_parts:
            description = " | ".join(description_parts) + "\n\n" + body_preview
        else:
            description = body_preview

        # Build URL
        dashboard_url = os.getenv("AVATARFACTORY_DASHBOARD_URL", "").rstrip("/")
        if not dashboard_url:
            dashboard_url = os.getenv("AVATARFACTORY_SERVICE_URL", "").rstrip("/")

        if dashboard_url and content_id:
            url = f"{dashboard_url}/content/{content_id}/view"
        else:
            url = ""

        title = f"📝 {content_title}"
        if len(title) > 60:
            title = title[:57] + "..."

        # If no URL, fall back to markdown format
        if not url:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {title}\n\n{description}"
                }
            }
        else:
            # Use news card format
            payload = {
                "msgtype": "news",
                "news": {
                    "articles": [
                        {
                            "title": title,
                            "description": description[:512],
                            "url": url,
                            "picurl": "",
                        }
                    ]
                }
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        logger.info(f"Sent content notification for task {task.id}")
                    else:
                        logger.warning(f"Content notification failed: {data.get('errmsg')}")
                else:
                    logger.warning(f"Content notification HTTP error: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to send content notification: {e}")

    async def _notify_task_failed(self, task: ScheduledTask, error: str) -> None:
        """Send notification when task fails."""
        import os
        import httpx
        from avatarfactory.notifications import ConsoleNotifier, NotificationMessage, NotificationPriority

        message = NotificationMessage(
            title=f"Task Failed: {task.name}",
            body=f"Error: {error}",
            priority=NotificationPriority.HIGH,
            category="error",
        )

        # Send to console for all task types
        console_notifier = ConsoleNotifier()
        await console_notifier.send(message)

        # Only send webhook notifications for discovery and content tasks
        if task.task_type not in ("topic", "discovery", "content"):
            return

        webhook_url = os.getenv("AVATARFACTORY_WEBHOOK_URL")
        if not webhook_url:
            return

        # Check if persona has notifications enabled
        if task.persona_id:
            from avatarfactory.core.knowledges_db import get_knowledge_base
            kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
            kb = get_knowledge_base(kb_path)
            persona = kb.load_persona(task.persona_id)
            if persona:
                if persona.notification is None or not persona.notification.enabled:
                    logger.debug(f"Skipping error notification for persona {task.persona_id}: notifications disabled")
                    return

        # Build error notification
        content = f"### ❌ 任务失败: {task.name}\n\n"
        content += f"**类型:** {task.task_type}\n"
        content += f"**错误:** {error[:500]}"

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        logger.info(f"Sent error notification for task {task.id}")
                    else:
                        logger.warning(f"Error notification failed: {data.get('errmsg')}")
                else:
                    logger.warning(f"Error notification HTTP error: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to send error notification: {e}")

    async def _process_publish_queue(self) -> None:
        """Process pending items in publish queue."""
        from avatarfactory.core.database.connection import get_session
        from avatarfactory.core.database.repositories.scheduler import PublishQueueRepository

        now = datetime.now()

        async with get_session() as session:
            repo = PublishQueueRepository(session)
            pending = await repo.list_pending(scheduled_before=now)

            for item in pending:
                try:
                    # Import and run publisher
                    from avatarfactory.scheduler.tasks import publish_content

                    publish_item = PublishQueueItem(
                        id=item.id,
                        content_id=item.content_id,
                        platform=item.platform,
                        scheduled_time=item.scheduled_time,
                        status=item.status,
                        created_at=item.created_at,
                    )
                    result = await publish_content(publish_item)

                    if result.get("success"):
                        await repo.mark_published(item.id, result.get("post_url"))
                    else:
                        await repo.mark_failed(item.id, result.get("error", "Unknown error"))

                    self._emit("content_published", {"item": item, "result": result})

                except Exception as e:
                    await repo.mark_failed(item.id, str(e))
                    self._emit("publish_failed", {"item": item, "error": str(e)})

    def _run_publish_queue(self) -> None:
        """Execute publish queue processing (synchronous wrapper)."""
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._process_publish_queue())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error processing publish queue: {e}")

    async def initialize(self) -> None:
        """Initialize scheduler by loading tasks from database."""
        await self._load_tasks_from_db()
        await self._ensure_system_tasks()

    def _sync_initialize(self) -> None:
        """Synchronous wrapper for initialize() to run in a thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.initialize())
        finally:
            loop.close()

    def start(self, blocking: bool = True) -> None:
        """Start the scheduler."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            raise ImportError("apscheduler required. Install with: pip install apscheduler")

        if self._running:
            logger.warning("Scheduler is already running")
            return

        # Initialize by loading tasks
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, schedule initialization as a task
            # The initialize will run in background
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._sync_initialize)
                future.result(timeout=30)  # Wait up to 30 seconds
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.initialize())
            finally:
                loop.close()

        self._scheduler = BackgroundScheduler()

        # Schedule all enabled tasks
        for task in self._tasks.values():
            self._schedule_task(task)

        # Add publish queue processor (every 5 minutes)
        self._scheduler.add_job(
            self._run_publish_queue,
            "interval",
            minutes=5,
            id="__publish_queue__",
        )

        self._scheduler.start()
        self._running = True

        logger.info("Scheduler started")
        self._emit("scheduler_started", {"tasks": len(self._tasks)})

        if blocking:
            # Set up signal handlers for graceful shutdown
            def signal_handler(sig, frame):
                logger.info("Shutdown signal received")
                self.stop()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            if hasattr(signal, 'SIGTERM'):
                signal.signal(signal.SIGTERM, signal_handler)

            # Keep running
            try:
                import time
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")
            self._emit("scheduler_stopped", {})

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    # =========================================================================
    # Status and Info
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "tasks_count": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
        }

    def get_next_runs(self) -> List[Dict[str, Any]]:
        """Get next scheduled run times."""
        if not self._scheduler or not self._running:
            return []

        jobs = self._scheduler.get_jobs()
        result = []
        for job in jobs:
            if job.id.startswith("__"):
                continue
            task = self._tasks.get(job.id)
            if task:
                result.append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                })
        return result


# =============================================================================
# Migration Utilities
# =============================================================================

async def migrate_tasks_from_json(data_dir: str = "./knowledges/scheduler") -> int:
    """
    Migrate tasks from JSON file to database.

    Args:
        data_dir: Path to scheduler data directory

    Returns:
        Number of tasks migrated
    """
    from avatarfactory.core.database.connection import get_session, init_database
    from avatarfactory.core.database.repositories.scheduler import SchedulerRepository

    tasks_file = Path(data_dir) / "tasks.json"
    if not tasks_file.exists():
        logger.info("No tasks.json found, nothing to migrate")
        return 0

    # Ensure database is initialized
    await init_database()

    # Load tasks from JSON
    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks_data = json.load(f)

    migrated = 0
    async with get_session() as session:
        repo = SchedulerRepository(session)

        for task_data in tasks_data:
            task_id = task_data.get("id")
            if not task_id:
                continue

            # Check if already exists
            existing = await repo.get(task_id)
            if existing:
                logger.debug(f"Task {task_id} already exists in database, skipping")
                continue

            # Create in database
            await repo.create_task(
                task_id=task_id,
                name=task_data.get("name", ""),
                task_type=task_data.get("task_type", ""),
                schedule=task_data.get("schedule", ""),
                enabled=task_data.get("enabled", True),
                persona_id=task_data.get("persona_id"),
                platform=task_data.get("platform"),
                extra_params=task_data.get("extra_params", {}),
            )

            # Update run stats if present
            if task_data.get("last_run") or task_data.get("run_count"):
                db_task = await repo.get(task_id)
                if db_task:
                    if task_data.get("last_run"):
                        try:
                            db_task.last_run = datetime.fromisoformat(task_data["last_run"])
                        except Exception:
                            pass
                    db_task.last_status = task_data.get("last_status")
                    db_task.last_error = task_data.get("last_error")
                    db_task.run_count = task_data.get("run_count", 0)
                    await session.flush()

            migrated += 1
            logger.info(f"Migrated task: {task_id}")

    logger.info(f"Migration complete: {migrated} tasks migrated")

    # Optionally backup the JSON file
    if migrated > 0:
        backup_file = tasks_file.with_suffix(".json.bak")
        tasks_file.rename(backup_file)
        logger.info(f"Backed up original file to {backup_file}")

    return migrated
