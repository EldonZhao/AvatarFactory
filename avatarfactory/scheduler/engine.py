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

        # Track file modification times to detect external changes
        self._tasks_file_mtime: Optional[float] = None
        self._queue_file_mtime: Optional[float] = None

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
                # Track file modification time
                self._tasks_file_mtime = tasks_file.stat().st_mtime

                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = ScheduledTask(**task_data)
                        self._tasks[task.id] = task
            except Exception as e:
                logger.warning(f"Failed to load tasks: {e}")

        if queue_file.exists():
            try:
                # Track file modification time
                self._queue_file_mtime = queue_file.stat().st_mtime

                with open(queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._publish_queue = [PublishQueueItem(**item) for item in data]
            except Exception as e:
                logger.warning(f"Failed to load publish queue: {e}")

    def _save_state(self) -> None:
        """
        Persist scheduler state with external modification detection.

        If the tasks file was modified externally since we loaded it,
        we merge changes instead of blindly overwriting:
        - Keep tasks from file that we don't have in memory (new tasks added externally)
        - Remove tasks from memory that were deleted from file externally
        - For tasks that exist in both, prefer memory state (has runtime updates like last_run)
        """
        tasks_file = self._data_dir / "tasks.json"
        queue_file = self._data_dir / "publish_queue.json"

        try:
            # Check if tasks file was modified externally
            if tasks_file.exists() and self._tasks_file_mtime is not None:
                current_mtime = tasks_file.stat().st_mtime
                if current_mtime > self._tasks_file_mtime:
                    logger.info("Detected external modification to tasks.json, merging changes...")
                    self._merge_external_task_changes(tasks_file)

            # Save tasks
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump([t.model_dump(mode='json') for t in self._tasks.values()], f, indent=2, default=str, ensure_ascii=False)

            # Update tracked mtime
            self._tasks_file_mtime = tasks_file.stat().st_mtime

            # Save publish queue
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump([q.model_dump(mode='json') for q in self._publish_queue], f, indent=2, default=str, ensure_ascii=False)

            if queue_file.exists():
                self._queue_file_mtime = queue_file.stat().st_mtime

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _merge_external_task_changes(self, tasks_file: Path) -> None:
        """
        Merge external changes to tasks.json with in-memory state.

        Strategy:
        - Tasks deleted from file externally -> remove from memory
        - Tasks added to file externally -> add to memory
        - Tasks modified in file -> keep memory version (has runtime state)
          but update static config (schedule, enabled, extra_params) from file
        """
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)

            file_tasks = {t["id"]: t for t in file_data}
            file_task_ids = set(file_tasks.keys())
            memory_task_ids = set(self._tasks.keys())

            # Tasks deleted externally (in memory but not in file)
            deleted_ids = memory_task_ids - file_task_ids
            for task_id in deleted_ids:
                logger.info(f"Task {task_id} was deleted externally, removing from memory")
                del self._tasks[task_id]
                # Also remove from APScheduler if running
                if self._running and self._scheduler:
                    try:
                        self._scheduler.remove_job(task_id)
                    except Exception:
                        pass

            # Tasks added externally (in file but not in memory)
            added_ids = file_task_ids - memory_task_ids
            for task_id in added_ids:
                logger.info(f"Task {task_id} was added externally, loading into memory")
                task = ScheduledTask(**file_tasks[task_id])
                self._tasks[task_id] = task
                # Schedule if running
                if self._running and self._scheduler:
                    self._schedule_task(task)

            # Tasks in both - merge config changes but keep runtime state
            common_ids = memory_task_ids & file_task_ids
            for task_id in common_ids:
                file_task = file_tasks[task_id]
                memory_task = self._tasks[task_id]

                # Update static config from file
                updated = False
                for field in ["name", "schedule", "enabled", "platform", "extra_params"]:
                    if field in file_task and getattr(memory_task, field) != file_task.get(field):
                        setattr(memory_task, field, file_task[field])
                        updated = True

                if updated:
                    logger.info(f"Task {task_id} config updated from external changes")
                    # Reschedule if running and schedule changed
                    if self._running and self._scheduler:
                        try:
                            self._scheduler.remove_job(task_id)
                        except Exception:
                            pass
                        if memory_task.enabled:
                            self._schedule_task(memory_task)

        except Exception as e:
            logger.warning(f"Failed to merge external task changes: {e}")

    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task."""
        self._tasks[task.id] = task
        self._save_state()

        if self._running and self._scheduler:
            self._schedule_task(task)

    def add_task_from_dict(self, task_dict: Dict[str, Any]) -> ScheduledTask:
        """
        Add a scheduled task from a dictionary.

        Args:
            task_dict: Dictionary with task properties (id, name, task_type, schedule, etc.)

        Returns:
            The created ScheduledTask
        """
        task = ScheduledTask(**task_dict)
        self.add_task(task)
        return task

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

    def remove_tasks_for_persona(self, persona_id: str) -> int:
        """Remove all scheduled tasks for a specific persona.

        Args:
            persona_id: The persona ID to remove tasks for

        Returns:
            Number of tasks removed
        """
        tasks_to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.persona_id == persona_id
        ]

        for task_id in tasks_to_remove:
            self.remove_task(task_id)

        return len(tasks_to_remove)

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

        # Send to console for all task types
        console_notifier = ConsoleNotifier()
        await console_notifier.send(message)

        # Send to webhook only for discovery and content tasks
        webhook_url = os.getenv("AVATARFACTORY_WEBHOOK_URL")
        if not webhook_url:
            return

        # Only send webhook notifications for discovery and content tasks
        if task.task_type == "discovery":
            # Discovery: Use markdown format for detailed report
            await self._send_discovery_webhook_notification(task, result, webhook_url)
        elif task.task_type == "content":
            # Content: Use news card format with link
            await self._send_content_webhook_notification(task, result, webhook_url)

    async def _send_discovery_webhook_notification(
        self, task: ScheduledTask, result: Dict[str, Any], webhook_url: str
    ) -> None:
        """
        Send discovery task notification using markdown format.

        Format includes:
        - Trending topics discovered
        - Generated ideas
        - Key insights
        """
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
                        logger.info(f"Sent discovery notification for task {task.id}")
                    else:
                        logger.warning(f"Discovery notification failed: {data.get('errmsg')}")
                else:
                    logger.warning(f"Discovery notification HTTP error: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to send discovery notification: {e}")

    async def _send_content_webhook_notification(
        self, task: ScheduledTask, result: Dict[str, Any], webhook_url: str
    ) -> None:
        """
        Send content task notification using news card format.

        Format includes:
        - Card title with content title
        - Description with review score and preview
        - Clickable link to view content in dashboard
        """
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

        # Build URL - link directly to the content preview page
        # Use AVATARFACTORY_DASHBOARD_URL if set, otherwise fallback to SERVICE_URL
        dashboard_url = os.getenv("AVATARFACTORY_DASHBOARD_URL", "").rstrip("/")
        if not dashboard_url:
            # In Azure deployment, dashboard is at the same URL
            dashboard_url = os.getenv("AVATARFACTORY_SERVICE_URL", "").rstrip("/")

        if dashboard_url and content_id:
            # Link to dedicated Preview page
            url = f"{dashboard_url}/Preview?id={content_id}"
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
                            "description": description[:512],  # Max 512 chars
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
        """
        Send notification when task fails.

        Only sends webhook notifications for discovery and content tasks.
        """
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
        if task.task_type not in ("discovery", "content"):
            return

        webhook_url = os.getenv("AVATARFACTORY_WEBHOOK_URL")
        if not webhook_url:
            return

        # Build error notification using markdown format
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
