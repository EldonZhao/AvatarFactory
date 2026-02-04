"""
AvatarFactory Notifications Module.

Provides notification delivery to various channels.
"""

from avatarfactory.notifications.base import (
    NotificationProvider,
    NotificationMessage,
    NotificationPriority,
)
from avatarfactory.notifications.console import ConsoleNotifier
from avatarfactory.notifications.webhook import WebhookNotifier

__all__ = [
    "NotificationProvider",
    "NotificationMessage",
    "NotificationPriority",
    "ConsoleNotifier",
    "WebhookNotifier",
]
