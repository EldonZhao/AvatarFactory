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

__all__ = [
    "BasePlatformConnector",
    "ConnectorConfig",
    "ConnectionStatus",
    "PublishResult",
    "FetchResult",
    "get_connector",
]


def get_connector(platform: str, config: ConnectorConfig) -> BasePlatformConnector:
    """
    Get platform connector instance.

    Args:
        platform: Platform name (twitter, bluesky, etc.)
        config: Connector configuration

    Returns:
        Platform connector instance

    Example:
        config = ConnectorConfig(api_key="...", api_secret="...")
        connector = get_connector("twitter", config)
        await connector.connect()
    """
    from avatarfactory.connectors.twitter import TwitterConnector
    from avatarfactory.connectors.bluesky import BlueskyConnector

    connectors = {
        "twitter": TwitterConnector,
        "bluesky": BlueskyConnector,
    }

    connector_class = connectors.get(platform.lower())
    if not connector_class:
        available = ", ".join(connectors.keys())
        raise ValueError(f"Unknown platform: {platform}. Available: {available}")

    return connector_class(config)
