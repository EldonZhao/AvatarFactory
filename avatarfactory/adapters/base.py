"""
Base platform adapter for AvatarFactory.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from avatarfactory.models.schemas import Content, PlatformType


class BasePlatformAdapter(ABC):
    """Base class for all platform adapters"""

    def __init__(self, platform: PlatformType):
        self.platform = platform

    @abstractmethod
    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get platform-specific content guidelines"""
        pass

    @abstractmethod
    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for this platform"""
        pass

    @abstractmethod
    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for platform export"""
        pass

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for this platform"""
        return []

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get hashtag strategy for this platform"""
        return {
            "recommended_count": 5,
            "max_count": 10,
            "placement": "end",
            "guidelines": [],
        }
