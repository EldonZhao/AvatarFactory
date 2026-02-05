"""
Scheduler Engine for AvatarFactory.

Provides task scheduling using APScheduler with persistence and management.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("avatarfactory.scheduler")


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    # Persistence
    data_dir: str = Field(default="./knowledges/scheduler")

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
        self._tasks: Dict[str, ScheduledTask] = {}
        self._publish_queue: List[PublishQueueItem] = []
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Ensure data directory exists
        self._data_dir = Path(self.config.data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted state
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted scheduler state."""
        tasks_file = self._data_dir / "tasks.json"
        queue_file = self._data_dir / "publish_queue.json"

        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = ScheduledTask(**task_data)
                        self._tasks[task.id] = task
            except Exception as e:
                logger.warning(f"Failed to load tasks: {e}")

        if queue_file.exists():
            try:
                with open(queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._publish_queue = [PublishQueueItem(**item) for item in data]
            except Exception as e:
                logger.warning(f"Failed to load publish queue: {e}")

    def _save_state(self) -> None:
        """Persist scheduler state."""
        tasks_file = self._data_dir / "tasks.json"
        queue_file = self._data_dir / "publish_queue.json"

        try:
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump([t.model_dump(mode='json') for t in self._tasks.values()], f, indent=2, default=str)

            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump([q.model_dump(mode='json') for q in self._publish_queue], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task."""
        self._tasks[task.id] = task
        self._save_state()

        if self._running and self._scheduler:
            self._schedule_task(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_state()

            if self._running and self._scheduler:
                try:
                    self._scheduler.remove_job(task_id)
                except Exception:
                    pass
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self._tasks.values())

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            self._save_state()
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            self._save_state()
            return True
        return False

    # =========================================================================
    # Publish Queue
    # =========================================================================

    def queue_publish(
        self,
        content_id: str,
        platform: str,
        scheduled_time: Optional[datetime] = None,
    ) -> PublishQueueItem:
        """Add content to the publish queue."""
        import uuid
        item = PublishQueueItem(
            id=f"pub_{uuid.uuid4().hex[:8]}",
            content_id=content_id,
            platform=platform,
            scheduled_time=scheduled_time,
        )
        self._publish_queue.append(item)
        self._save_state()
        return item

    def get_publish_queue(self, status: Optional[str] = None) -> List[PublishQueueItem]:
        """Get publish queue items."""
        if status:
            return [q for q in self._publish_queue if q.status == status]
        return self._publish_queue.copy()

    def remove_from_queue(self, item_id: str) -> bool:
        """Remove item from publish queue."""
        for i, item in enumerate(self._publish_queue):
            if item.id == item_id:
                self._publish_queue.pop(i)
                self._save_state()
                return True
        return False

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

        self._save_state()

    async def _notify_task_completed(self, task: ScheduledTask, result: Dict[str, Any]) -> None:
        """Send notification when task completes."""
        from avatarfactory.notifications import ConsoleNotifier, NotificationMessage, NotificationPriority

        notifier = ConsoleNotifier()

        if task.task_type == "discovery":
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

        await notifier.send(message)

    async def _notify_task_failed(self, task: ScheduledTask, error: str) -> None:
        """Send notification when task fails."""
        from avatarfactory.notifications import ConsoleNotifier, NotificationMessage, NotificationPriority

        notifier = ConsoleNotifier()

        message = NotificationMessage(
            title=f"Task Failed: {task.name}",
            body=f"Error: {error}",
            priority=NotificationPriority.HIGH,
            category="error",
        )

        await notifier.send(message)

    async def _process_publish_queue(self) -> None:
        """Process pending items in publish queue."""
        now = datetime.now()
        pending = [
            q for q in self._publish_queue
            if q.status == "pending"
            and (q.scheduled_time is None or q.scheduled_time <= now)
        ]

        for item in pending:
            try:
                # Import and run publisher
                from avatarfactory.scheduler.tasks import publish_content

                result = await publish_content(item)
                item.status = "published" if result.get("success") else "failed"
                item.published_at = datetime.now()
                item.post_url = result.get("post_url")
                item.error = result.get("error")

                self._emit("content_published", {"item": item, "result": result})

            except Exception as e:
                item.status = "failed"
                item.error = str(e)
                self._emit("publish_failed", {"item": item, "error": str(e)})

        self._save_state()

    def start(self, blocking: bool = True) -> None:
        """Start the scheduler."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            raise ImportError("apscheduler required. Install with: pip install apscheduler")

        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._scheduler = BackgroundScheduler()

        # Schedule all enabled tasks
        for task in self._tasks.values():
            self._schedule_task(task)

        # Add publish queue processor (every 5 minutes)
        self._scheduler.add_job(
            self._process_publish_queue,
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

            # Keep running - use a simple loop that works with AsyncIOScheduler
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
            self._save_state()
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
            "queue_pending": sum(1 for q in self._publish_queue if q.status == "pending"),
            "queue_published": sum(1 for q in self._publish_queue if q.status == "published"),
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
