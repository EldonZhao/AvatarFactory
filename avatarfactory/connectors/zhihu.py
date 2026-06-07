"""
Zhihu (知乎) platform connector.

Zhihu is a Chinese Q&A platform similar to Quora.
Note: Official API is limited. This connector uses cookie-based authentication.
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


@ConnectorRegistry.register_decorator("zhihu")
class ZhihuConnector(BasePlatformConnector):
    """
    Zhihu platform connector using cookie-based authentication.

    Required credentials:
    - cookie: Browser cookie string (from logged-in session)

    Optional:
    - user_id: Zhihu user ID (url_token)
    """

    API_BASE = "https://www.zhihu.com/api/v4"
    WEB_BASE = "https://www.zhihu.com"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._cookie: Optional[str] = None
        self._user_id: Optional[str] = None
        self._user_name: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "zhihu"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="zhihu",
            display_name="Zhihu (知乎)",
            description="Zhihu Q&A and knowledge platform",
            supports_topic_discovery=True,
            supports_persona_discovery=True,
            supports_publishing=False,
            supports_fetching=True,
            config_fields=[
                ConnectorConfigField(
                    name="cookie",
                    label="Cookie",
                    field_type="textarea",
                    required=True,
                    description=("Browser cookie string" " (extract from browser DevTools)"),
                    placeholder="Paste cookie string from browser",
                    env_var="ZHIHU_COOKIE",
                ),
                ConnectorConfigField(
                    name="user_id",
                    label="User URL Token",
                    field_type="text",
                    required=False,
                    description=("Zhihu user URL token for fetching user content"),
                    env_var="ZHIHU_USER_ID",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Requires cookie-based"
                " auth. Call connector.fetch_trending() for Zhihu hot"
                " questions and trending topics. Call"
                " connector.fetch_user_posts(user_id) to analyze expert"
                " content for persona research. connector.search(query)"
                " provides topic-specific Q&A analysis. Publishing is not"
                " supported due to complex authentication requirements."
                " Best used for topic and persona discovery in"
                " professional/knowledge domains."
            ),
        )

    async def connect(self) -> bool:
        """Connect to Zhihu using cookie authentication."""
        cookie = self.config.extra.get("cookie") or os.getenv("ZHIHU_COOKIE")

        if not cookie:
            self.status = ConnectionStatus.ERROR
            raise ValueError(
                "Zhihu requires cookie authentication. Set ZHIHU_COOKIE env var "
                "or pass cookie in config.extra."
            )

        self._cookie = cookie
        self._user_id = self.config.extra.get("user_id") or os.getenv("ZHIHU_USER_ID")
        self.status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> None:
        """Disconnect from Zhihu."""
        self._cookie = None
        self._user_id = None
        self._user_name = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify cookie is valid by fetching user info."""
        if not self._cookie:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/me",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    self._user_id = data.get("url_token")
                    self._user_name = data.get("name")
                    return True
                return False
        except Exception:
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with cookie."""
        return {
            "Cookie": self._cookie or "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.zhihu.com/",
            "x-requested-with": "fetch",
        }

    async def fetch_posts(self, limit: int = 20, **kwargs) -> FetchResult:
        """
        Fetch hot questions or search results from Zhihu.

        Args:
            limit: Maximum number of results
            query: Search query (optional, fetches hot questions if not provided)
            content_type: "question", "answer", or "article" (default: "question")

        Returns:
            FetchResult with questions/answers
        """
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for Zhihu connector. Install with: pip install httpx")

        if not self._cookie:
            return FetchResult(success=False, error="Not connected")

        query = kwargs.get("query")
        try:
            async with httpx.AsyncClient() as client:
                if query:
                    # Search
                    response = await client.get(
                        f"{self.API_BASE}/search_v3",
                        params={
                            "t": "general",
                            "q": query,
                            "correction": 1,
                            "offset": 0,
                            "limit": min(limit, 20),
                        },
                        headers=self._get_headers(),
                        timeout=30.0,
                    )
                else:
                    # Get hot questions
                    response = await client.get(
                        f"{self.API_BASE}/questions/hot",
                        params={
                            "limit": min(limit, 50),
                        },
                        headers=self._get_headers(),
                        timeout=30.0,
                    )

                if response.status_code != 200:
                    return FetchResult(
                        success=False,
                        error=f"API error: {response.status_code}",
                    )

                data = response.json()
                results = []

                # Parse results based on endpoint
                items = data.get("data", [])
                for item in items[:limit]:
                    # Handle different item types
                    if "target" in item:
                        target = item.get("target", {})
                    else:
                        target = item

                    item_type = target.get("type", "question")

                    if item_type == "question":
                        results.append(
                            {
                                "id": str(target.get("id", "")),
                                "title": target.get("title", ""),
                                "description": target.get("excerpt", ""),
                                "url": f"{self.WEB_BASE}/question/{target.get('id', '')}",
                                "source": "zhihu_question",
                                "answer_count": target.get("answer_count", 0),
                                "follower_count": target.get("follower_count", 0),
                                "created_at": target.get("created"),
                            }
                        )
                    elif item_type == "answer":
                        question = target.get("question", {})
                        author = target.get("author", {})
                        results.append(
                            {
                                "id": str(target.get("id", "")),
                                "title": question.get("title", ""),
                                "description": target.get("excerpt", ""),
                                "url": f"{self.WEB_BASE}/answer/{target.get('id', '')}",
                                "source": "zhihu_answer",
                                "author": author.get("name", ""),
                                "voteup_count": target.get("voteup_count", 0),
                                "comment_count": target.get("comment_count", 0),
                                "created_at": target.get("created_time"),
                            }
                        )
                    elif item_type == "article":
                        author = target.get("author", {})
                        results.append(
                            {
                                "id": str(target.get("id", "")),
                                "title": target.get("title", ""),
                                "description": target.get("excerpt", ""),
                                "url": f"{self.WEB_BASE}/p/{target.get('id', '')}",
                                "source": "zhihu_article",
                                "author": author.get("name", ""),
                                "voteup_count": target.get("voteup_count", 0),
                                "comment_count": target.get("comment_count", 0),
                                "created_at": target.get("created"),
                            }
                        )

                return FetchResult(
                    success=True,
                    posts=results,
                    cursor=data.get("paging", {}).get("next"),
                )

        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def publish(self, content: Any, **kwargs) -> PublishResult:
        """
        Publish content to Zhihu.

        Note: Publishing to Zhihu requires more complex flows (answering questions,
        writing articles, etc.) and may require additional authentication.
        This is currently a placeholder for future implementation.
        """
        return PublishResult(
            success=False,
            error="Zhihu publishing requires complex authentication flows. "
            "Use the web interface for now.",
        )

    async def search(self, query: str, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for content on Zhihu.

        Args:
            query: Search query
            limit: Maximum results
            content_type: "question", "answer", or "article"

        Returns:
            List of search results
        """
        result = await self.fetch_posts(limit=limit, query=query, **kwargs)
        return result.posts if result.success else []

    async def fetch_hot_topics(self, limit: int = 50) -> FetchResult:
        """
        Fetch hot topics from Zhihu's trending list.

        Returns:
            FetchResult with hot topics
        """
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for Zhihu connector. Install with: pip install httpx")

        if not self._cookie:
            return FetchResult(success=False, error="Not connected")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.WEB_BASE}/api/v3/feed/topstory/hot-lists/total",
                    params={"limit": min(limit, 50)},
                    headers=self._get_headers(),
                    timeout=30.0,
                )

                if response.status_code != 200:
                    return FetchResult(
                        success=False,
                        error=f"API error: {response.status_code}",
                    )

                data = response.json()
                results = []

                for item in data.get("data", [])[:limit]:
                    target = item.get("target", {})
                    results.append(
                        {
                            "id": str(target.get("id", "")),
                            "title": target.get("title", ""),
                            "description": target.get("excerpt", ""),
                            "url": f"{self.WEB_BASE}/question/{target.get('id', '')}",
                            "source": "zhihu_hot",
                            "heat": item.get("detail_text", ""),
                            "answer_count": target.get("answer_count", 0),
                        }
                    )

                return FetchResult(
                    success=True,
                    posts=results,
                    cursor=None,
                )

        except Exception as e:
            return FetchResult(success=False, error=str(e))
