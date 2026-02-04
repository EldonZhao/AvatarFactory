"""
Base notification provider for AvatarFactory.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationMessage(BaseModel):
    """Notification message structure."""

    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body/content")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)

    # Optional fields
    category: Optional[str] = None  # task_completed, content_published, error, etc.
    action_url: Optional[str] = None  # URL for action button
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.now)


class NotificationResult(BaseModel):
    """Result of sending a notification."""

    success: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: datetime = Field(default_factory=datetime.now)


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    def __init__(self, name: str):
        self.name = name
        self._enabled = True

    @abstractmethod
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """
        Send a notification.

        Args:
            message: NotificationMessage to send

        Returns:
            NotificationResult with success status
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate provider configuration.

        Returns:
            True if configuration is valid
        """
        pass

    def enable(self) -> None:
        """Enable this provider."""
        self._enabled = True

    def disable(self) -> None:
        """Disable this provider."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if provider is enabled."""
        return self._enabled


class NotificationManager:
    """
    Manages multiple notification providers.

    Sends notifications through all enabled providers.
    """

    def __init__(self):
        self._providers: Dict[str, NotificationProvider] = {}

    def add_provider(self, provider: NotificationProvider) -> None:
        """Add a notification provider."""
        self._providers[provider.name] = provider

    def remove_provider(self, name: str) -> bool:
        """Remove a notification provider."""
        if name in self._providers:
            del self._providers[name]
            return True
        return False

    def get_provider(self, name: str) -> Optional[NotificationProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all provider names."""
        return list(self._providers.keys())

    async def send(
        self,
        message: NotificationMessage,
        providers: Optional[List[str]] = None,
    ) -> List[NotificationResult]:
        """
        Send notification through specified or all enabled providers.

        Args:
            message: NotificationMessage to send
            providers: Optional list of provider names (uses all enabled if not specified)

        Returns:
            List of NotificationResult from each provider
        """
        results = []

        if providers:
            target_providers = [
                self._providers[name]
                for name in providers
                if name in self._providers
            ]
        else:
            target_providers = [
                p for p in self._providers.values() if p.is_enabled()
            ]

        for provider in target_providers:
            try:
                result = await provider.send(message)
                results.append(result)
            except Exception as e:
                results.append(NotificationResult(
                    success=False,
                    provider=provider.name,
                    error=str(e),
                ))

        return results

    async def send_simple(
        self,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: Optional[str] = None,
    ) -> List[NotificationResult]:
        """
        Convenience method to send a simple notification.

        Args:
            title: Notification title
            body: Notification body
            priority: Notification priority
            category: Optional category

        Returns:
            List of NotificationResult
        """
        message = NotificationMessage(
            title=title,
            body=body,
            priority=priority,
            category=category,
        )
        return await self.send(message)
