"""
Brave Search API connector.

Brave Search provides privacy-focused web search with a generous free tier.
Documentation: https://api.search.brave.com/
"""

import os
from typing import Any, Dict, List, Optional

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorCapabilities,
    ConnectorConfig,
    ConnectorConfigField,
    FetchResult,
    IntegrationType,
    PublishResult,
)
from avatarfactory.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register_decorator("brave_search")
class BraveSearchConnector(BasePlatformConnector):
    """Brave Search API connector for web search."""

    BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "brave_search"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="brave_search",
            display_name="Brave Search",
            description="Brave Search API for web and news results",
            supports_topic_discovery=True,
            supports_persona_discovery=False,
            supports_publishing=False,
            supports_fetching=True,
            config_fields=[
                ConnectorConfigField(
                    name="api_key",
                    label="API Key",
                    field_type="password",
                    required=True,
                    description="Brave Search API key",
                    env_var="BRAVE_SEARCH_API_KEY",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. A read-only search"
                " connector for web content. Call"
                " connector.fetch_trending(query) for web and news search"
                " results. Privacy-focused alternative to Bing Search for"
                " topic discovery. Does not support publishing or"
                " user-specific content fetching. Best used as a"
                " supplementary source for broad trend analysis."
            ),
        )

    async def connect(self) -> bool:
        """Initialize connection with API key."""
        api_key = self.config.api_key or os.getenv("BRAVE_SEARCH_API_KEY")

        if not api_key:
            self.status = ConnectionStatus.ERROR
            raise ValueError(
                "Brave Search requires API key. Set BRAVE_SEARCH_API_KEY env var "
                "or pass api_key in config."
            )

        self._api_key = api_key
        self.status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> None:
        """Disconnect from Brave Search."""
        self._api_key = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify API key is valid by making a test request."""
        if not self._api_key:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/web/search",
                    params={"q": "test", "count": 1},
                    headers={"X-Subscription-Token": self._api_key},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_posts(self, limit: int = 20, **kwargs) -> FetchResult:
        """
        Search web content using Brave Search.

        Args:
            limit: Maximum number of results
            query: Search query (required in kwargs)
            search_type: "web" or "news" (default: "web")

        Returns:
            FetchResult with search results
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Brave Search connector. Install with: pip install httpx"
            )

        if not self._api_key:
            return FetchResult(success=False, error="Not connected")

        query = kwargs.get("query", "trending topics")
        search_type = kwargs.get("search_type", "web")

        endpoint = f"{self.BASE_URL}/{search_type}/search"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params={
                        "q": query,
                        "count": min(limit, 20),  # Brave limits to 20 per request
                        "text_decorations": False,
                    },
                    headers={
                        "X-Subscription-Token": self._api_key,
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return FetchResult(
                        success=False,
                        error=f"API error: {response.status_code}",
                    )

                data = response.json()
                results = []

                # Parse web results
                web_results = data.get("web", {}).get("results", [])
                for item in web_results[:limit]:
                    results.append({
                        "id": item.get("url", ""),
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "url": item.get("url", ""),
                        "source": "brave_search",
                        "created_at": None,
                    })

                # Also check news results if available
                news_results = data.get("news", {}).get("results", [])
                for item in news_results[:limit]:
                    results.append({
                        "id": item.get("url", ""),
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "url": item.get("url", ""),
                        "source": "brave_search_news",
                        "created_at": item.get("age"),
                    })

                return FetchResult(
                    success=True,
                    posts=results[:limit],
                    cursor=None,
                )

        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def publish(self, content: Any, **kwargs) -> PublishResult:
        """
        Brave Search is read-only, publishing not supported.
        """
        return PublishResult(
            success=False,
            error="Brave Search is a read-only search connector. Publishing not supported.",
        )

    async def search(self, query: str, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for content using Brave Search API.

        Args:
            query: Search query
            limit: Maximum results
            search_type: "web" or "news"

        Returns:
            List of search results
        """
        result = await self.fetch_posts(limit=limit, query=query, **kwargs)
        return result.posts if result.success else []
