"""
Bing Search API connector.

Bing Search provides web, news, and image search via Azure Cognitive Services.
Documentation: https://docs.microsoft.com/en-us/azure/cognitive-services/bing-web-search/
"""

import os
from typing import Any, Dict, List, Optional

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorConfig,
    FetchResult,
    PublishResult,
)
from avatarfactory.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register_decorator("bing_search")
class BingSearchConnector(BasePlatformConnector):
    """Bing Search API connector for web/news search."""

    DEFAULT_ENDPOINT = "https://api.bing.microsoft.com/v7.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key: Optional[str] = None
        self._endpoint: str = self.DEFAULT_ENDPOINT

    @property
    def platform_name(self) -> str:
        return "bing_search"

    async def connect(self) -> bool:
        """Initialize connection with API key."""
        api_key = self.config.api_key or os.getenv("BING_SEARCH_API_KEY")
        endpoint = os.getenv("BING_SEARCH_ENDPOINT", self.DEFAULT_ENDPOINT)

        if not api_key:
            self.status = ConnectionStatus.ERROR
            raise ValueError(
                "Bing Search requires API key. Set BING_SEARCH_API_KEY env var "
                "or pass api_key in config."
            )

        self._api_key = api_key
        self._endpoint = endpoint
        self.status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> None:
        """Disconnect from Bing Search."""
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
                    f"{self._endpoint}/search",
                    params={"q": "test", "count": 1},
                    headers={"Ocp-Apim-Subscription-Key": self._api_key},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_posts(self, limit: int = 20, **kwargs) -> FetchResult:
        """
        Search content using Bing Search API.

        Args:
            limit: Maximum number of results
            query: Search query (required in kwargs)
            search_type: "web", "news", or "images" (default: "web")
            market: Market code like "en-US" or "zh-CN"

        Returns:
            FetchResult with search results
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Bing Search connector. Install with: pip install httpx"
            )

        if not self._api_key:
            return FetchResult(success=False, error="Not connected")

        query = kwargs.get("query", "trending topics")
        search_type = kwargs.get("search_type", "web")
        market = kwargs.get("market", "en-US")

        # Map search type to endpoint
        endpoint_map = {
            "web": "/search",
            "news": "/news/search",
            "images": "/images/search",
        }
        endpoint = f"{self._endpoint}{endpoint_map.get(search_type, '/search')}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params={
                        "q": query,
                        "count": min(limit, 50),  # Bing allows up to 50
                        "mkt": market,
                        "safeSearch": "Moderate",
                    },
                    headers={
                        "Ocp-Apim-Subscription-Key": self._api_key,
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

                # Parse based on search type
                if search_type == "web":
                    web_pages = data.get("webPages", {}).get("value", [])
                    for item in web_pages[:limit]:
                        results.append({
                            "id": item.get("url", ""),
                            "title": item.get("name", ""),
                            "description": item.get("snippet", ""),
                            "url": item.get("url", ""),
                            "source": "bing_search",
                            "created_at": item.get("dateLastCrawled"),
                        })
                elif search_type == "news":
                    news_items = data.get("value", [])
                    for item in news_items[:limit]:
                        results.append({
                            "id": item.get("url", ""),
                            "title": item.get("name", ""),
                            "description": item.get("description", ""),
                            "url": item.get("url", ""),
                            "source": "bing_news",
                            "created_at": item.get("datePublished"),
                            "provider": item.get("provider", [{}])[0].get("name", ""),
                        })
                elif search_type == "images":
                    images = data.get("value", [])
                    for item in images[:limit]:
                        results.append({
                            "id": item.get("contentUrl", ""),
                            "title": item.get("name", ""),
                            "description": "",
                            "url": item.get("hostPageUrl", ""),
                            "thumbnail_url": item.get("thumbnailUrl", ""),
                            "source": "bing_images",
                        })

                return FetchResult(
                    success=True,
                    posts=results,
                    cursor=None,
                )

        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def publish(self, content: Any, **kwargs) -> PublishResult:
        """
        Bing Search is read-only, publishing not supported.
        """
        return PublishResult(
            success=False,
            error="Bing Search is a read-only search connector. Publishing not supported.",
        )

    async def search(self, query: str, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for content using Bing Search API.

        Args:
            query: Search query
            limit: Maximum results
            search_type: "web", "news", or "images"
            market: Market code (e.g., "en-US", "zh-CN")

        Returns:
            List of search results
        """
        result = await self.fetch_posts(limit=limit, query=query, **kwargs)
        return result.posts if result.success else []
