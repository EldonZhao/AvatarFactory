"""
Connector Registry for AvatarFactory.

Provides dynamic connector registration and factory functionality.
"""

import logging
from typing import Dict, List, Optional, Type

from avatarfactory.connectors.base import BasePlatformConnector, ConnectorConfig

logger = logging.getLogger("avatarfactory.connectors.registry")


class ConnectorRegistry:
    """
    Dynamic connector registry for platform connectors.

    Supports:
    - Decorator-based registration
    - Runtime registration
    - Lazy instantiation with caching
    - Platform aliases (e.g., "xhs" for "xiaohongshu")
    """

    _connectors: Dict[str, Type[BasePlatformConnector]] = {}
    _instances: Dict[str, BasePlatformConnector] = {}

    @classmethod
    def register(cls, platform: str, connector_class: Type[BasePlatformConnector]) -> None:
        """
        Register a connector class for a platform.

        Args:
            platform: Platform name (lowercase)
            connector_class: Connector class to register
        """
        platform_key = platform.lower()
        cls._connectors[platform_key] = connector_class
        logger.debug(f"Registered connector for platform: {platform_key}")

    @classmethod
    def register_decorator(cls, platform: str):
        """
        Decorator to register a connector class.

        Usage:
            @ConnectorRegistry.register_decorator("twitter")
            class TwitterConnector(BasePlatformConnector):
                ...

        Args:
            platform: Platform name to register under

        Returns:
            Decorator function
        """
        def decorator(connector_class: Type[BasePlatformConnector]):
            cls.register(platform, connector_class)
            return connector_class
        return decorator

    @classmethod
    def get_connector_class(cls, platform: str) -> Optional[Type[BasePlatformConnector]]:
        """
        Get connector class for a platform.

        Args:
            platform: Platform name

        Returns:
            Connector class or None if not registered
        """
        return cls._connectors.get(platform.lower())

    @classmethod
    def create_connector(
        cls,
        platform: str,
        config: ConnectorConfig,
        use_cache: bool = False,
    ) -> BasePlatformConnector:
        """
        Create a connector instance for a platform.

        Args:
            platform: Platform name
            config: Connector configuration
            use_cache: Whether to cache and reuse connector instances

        Returns:
            Connector instance

        Raises:
            ValueError: If platform is not registered
        """
        platform_key = platform.lower()
        connector_class = cls._connectors.get(platform_key)

        if not connector_class:
            available = ", ".join(cls._connectors.keys())
            raise ValueError(
                f"Unknown platform: {platform}. "
                f"Available platforms: {available}"
            )

        if use_cache:
            cache_key = f"{platform_key}:{id(config)}"
            if cache_key in cls._instances:
                return cls._instances[cache_key]

            instance = connector_class(config)
            cls._instances[cache_key] = instance
            return instance

        return connector_class(config)

    @classmethod
    def list_platforms(cls) -> List[str]:
        """
        List all registered platform names.

        Returns:
            List of platform names
        """
        return list(cls._connectors.keys())

    @classmethod
    def is_registered(cls, platform: str) -> bool:
        """
        Check if a platform is registered.

        Args:
            platform: Platform name

        Returns:
            True if registered
        """
        return platform.lower() in cls._connectors

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached connector instances."""
        cls._instances.clear()

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered connectors (for testing)."""
        cls._connectors.clear()
        cls._instances.clear()
