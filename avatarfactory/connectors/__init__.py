"""
Platform connectors for AvatarFactory.

Connectors provide actual API integration with social platforms,
supporting content publishing, data fetching, and authentication.

Connectors are different from Adapters:
- Adapters: Content formatting and validation (offline)
- Connectors: API integration and network operations (online)
"""

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectorConfig,
    ConnectionStatus,
    PublishResult,
    FetchResult,
)
from avatarfactory.connectors.registry import ConnectorRegistry

# Import connectors to trigger registration
from avatarfactory.connectors import twitter, bluesky, xiaohongshu, wecom

__all__ = [
    "BasePlatformConnector",
    "ConnectorConfig",
    "ConnectionStatus",
    "PublishResult",
    "FetchResult",
    "ConnectorRegistry",
    "get_connector",
    "list_platforms",
]


def get_connector(platform: str, config: ConnectorConfig) -> BasePlatformConnector:
    """
    Get platform connector instance.

    This is a convenience function that delegates to ConnectorRegistry.
    For more control, use ConnectorRegistry directly.

    Args:
        platform: Platform name (twitter, bluesky, xiaohongshu, xhs, etc.)
        config: Connector configuration

    Returns:
        Platform connector instance

    Example:
        config = ConnectorConfig(api_key="...", api_secret="...")
        connector = get_connector("twitter", config)
        await connector.connect()
    """
    return ConnectorRegistry.create_connector(platform, config)


def list_platforms() -> list:
    """
    List all available platform names.

    Returns:
        List of registered platform names
    """
    return ConnectorRegistry.list_platforms()
