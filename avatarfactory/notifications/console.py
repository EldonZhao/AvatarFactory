"""
Console notification provider - outputs to terminal.
"""

import logging
from datetime import datetime

from avatarfactory.notifications.base import (
    NotificationMessage,
    NotificationProvider,
    NotificationResult,
)

logger = logging.getLogger("avatarfactory.notifications.console")


class ConsoleNotifier(NotificationProvider):
    """
    Console notification provider.

    Outputs notifications to the terminal/console.
    Useful for development and when running in foreground mode.
    """

    def __init__(self, use_rich: bool = True):
        super().__init__("console")
        self.use_rich = use_rich

    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Send notification to console."""
        try:
            if self.use_rich:
                self._send_rich(message)
            else:
                self._send_plain(message)

            return NotificationResult(
                success=True,
                provider=self.name,
                message_id=f"console_{datetime.now().timestamp()}",
            )
        except Exception as e:
            return NotificationResult(
                success=False,
                provider=self.name,
                error=str(e),
            )

    def _send_rich(self, message: NotificationMessage) -> None:
        """Send using rich formatting."""
        try:
            from rich.console import Console
            from rich.panel import Panel

            console = Console()

            # Color based on priority
            border_style = {
                "low": "dim",
                "normal": "cyan",
                "high": "yellow",
                "urgent": "red bold",
            }.get(message.priority.value, "cyan")

            # Category emoji
            emoji = {
                "task_completed": "✅",
                "content_published": "📤",
                "error": "❌",
                "warning": "⚠️",
                "topic": "🔍",
                "discovery": "🔍",
                "report": "📊",
            }.get(message.category or "", "📬")

            panel = Panel(
                f"{message.body}",
                title=f"{emoji} {message.title}",
                border_style=border_style,
            )
            console.print(panel)

        except ImportError:
            self._send_plain(message)

    def _send_plain(self, message: NotificationMessage) -> None:
        """Send using plain text."""
        priority_marker = {
            "low": "[LOW]",
            "normal": "[INFO]",
            "high": "[HIGH]",
            "urgent": "[URGENT]",
        }.get(message.priority.value, "[INFO]")

        print(f"\n{priority_marker} {message.title}")
        print(f"  {message.body}")
        if message.action_url:
            print(f"  Link: {message.action_url}")
        print()

    def validate_config(self) -> bool:
        """Console provider is always valid."""
        return True
