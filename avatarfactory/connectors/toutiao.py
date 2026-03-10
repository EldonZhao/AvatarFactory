"""
Toutiao (今日头条/头条号) platform connector.

Toutiao uses OAuth 2.0 for authentication.
Documentation: https://open.mp.toutiao.com/
"""

from datetime import datetime
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


@ConnectorRegistry.register_decorator("toutiao")
class ToutiaoConnector(BasePlatformConnector):
    """
    Toutiao (今日头条) platform connector using OAuth 2.0.

    Required credentials:
    - access_token: OAuth 2.0 access token from Toutiao Open Platform

    Optional:
    - client_key: App client key
    - client_secret: App client secret (for token refresh)
    """

    API_BASE = "https://open.snssdk.com"
    CONTENT_API = "https://open.toutiao.com"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._user_id: Optional[str] = None
        self._screen_name: Optional[str] = None
        self._avatar_url: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "toutiao"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="toutiao",
            display_name="Toutiao (今日头条)",
            description="Toutiao/Jinri Toutiao content platform",
            supports_topic_discovery=True,
            supports_persona_discovery=True,
            supports_publishing=True,
            supports_fetching=True,
            config_fields=[
                ConnectorConfigField(
                    name="access_token",
                    label="Access Token",
                    field_type="password",
                    required=True,
                    description="Toutiao OAuth 2.0 access token",
                    env_var="TOUTIAO_ACCESS_TOKEN",
                ),
                ConnectorConfigField(
                    name="client_key",
                    label="Client Key",
                    field_type="text",
                    required=False,
                    description=(
                        "Toutiao app client key (for token refresh)"
                    ),
                    env_var="TOUTIAO_CLIENT_KEY",
                ),
                ConnectorConfigField(
                    name="client_secret",
                    label="Client Secret",
                    field_type="password",
                    required=False,
                    description=(
                        "Toutiao app client secret (for token refresh)"
                    ),
                    env_var="TOUTIAO_CLIENT_SECRET",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Call"
                " connector.fetch_trending() for Toutiao hot list and"
                " trending articles. Call"
                " connector.fetch_user_posts(user_id) for user content"
                " analysis. Call connector.publish(content, title, images)"
                " to publish articles (图文) or microblogs (微头条)."
                " Toutiao's recommendation algorithm provides strong topic"
                " trend signals."
            ),
        )

    async def connect(self) -> bool:
        """Connect to Toutiao using OAuth access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Toutiao connector. Install with: pip install httpx"
            )

        if not self.config.access_token:
            raise ValueError("Toutiao requires access_token from OAuth 2.0 flow")

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                # Get user info to verify token
                response = await client.get(
                    f"{self.API_BASE}/oauth/userinfo/",
                    params={
                        "access_token": self.config.access_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error_code", 0) == 0:
                        user_data = data.get("data", {})
                        self._user_id = str(user_data.get("uid", user_data.get("open_id", "")))
                        self._screen_name = user_data.get("screen_name", user_data.get("nickname", ""))
                        self._avatar_url = user_data.get("avatar_url", "")

                        self.status = ConnectionStatus.CONNECTED
                        return True
                    else:
                        error = data.get("message", "Unknown error")
                        raise ValueError(f"Authentication failed: {error}")
                else:
                    raise ValueError(f"Authentication failed: HTTP {response.status_code}")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to Toutiao: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Toutiao."""
        self._user_id = None
        self._screen_name = None
        self._avatar_url = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid."""
        if not self.config.access_token:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/oauth/userinfo/",
                    params={
                        "access_token": self.config.access_token,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("error_code", -1) == 0
                return False
        except Exception:
            return False

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish an article or microblog to Toutiao.

        Args:
            content: Article content (HTML supported for articles)
            title: Article title (required for articles, optional for microblogs)
            images: Optional list of image paths (will be uploaded)
            tags: Tags for categorization
            article_type: 'article' or 'micro' (default: auto-detect based on title)
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Toutiao",
                platform=self.platform_name,
            )

        try:
            import httpx

            article_type = kwargs.get("article_type")
            if not article_type:
                # Auto-detect: if has title, treat as article; otherwise microblog
                article_type = "article" if title else "micro"

            async with httpx.AsyncClient() as client:
                if article_type == "article":
                    # Publish as article (图文)
                    result = await self._publish_article(
                        client, title or "Untitled", content, images, tags
                    )
                else:
                    # Publish as microblog (微头条)
                    result = await self._publish_micro(
                        client, content, images, tags
                    )

                return result

        except Exception as e:
            return PublishResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def _publish_article(
        self,
        client: Any,
        title: str,
        content: str,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> PublishResult:
        """Publish an article (图文文章)."""
        # Upload cover image if provided
        cover_image_url = ""
        if images and len(images) > 0:
            upload_result = await self._upload_image(client, images[0])
            if upload_result:
                cover_image_url = upload_result

        payload = {
            "access_token": self.config.access_token,
            "title": title[:30],  # Title max 30 chars
            "content": content,
            "article_type": "news",  # news, video, gallery
        }

        if cover_image_url:
            payload["cover_images"] = [cover_image_url]

        if tags:
            payload["tags"] = ",".join(tags[:5])  # Max 5 tags

        response = await client.post(
            f"{self.CONTENT_API}/article/publish/",
            json=payload,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("error_code", 0) == 0:
                result_data = data.get("data", {})
                return PublishResult(
                    success=True,
                    post_id=str(result_data.get("item_id", result_data.get("article_id", ""))),
                    post_url=result_data.get("share_url", ""),
                    platform=self.platform_name,
                    published_at=datetime.utcnow(),
                    raw_response=data,
                )
            else:
                return PublishResult(
                    success=False,
                    error=data.get("message", "Unknown error"),
                    platform=self.platform_name,
                )
        else:
            return PublishResult(
                success=False,
                error=f"HTTP {response.status_code}",
                platform=self.platform_name,
            )

    async def _publish_micro(
        self,
        client: Any,
        content: str,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> PublishResult:
        """Publish a microblog (微头条)."""
        # Upload images if provided
        image_urls = []
        if images:
            for image_path in images[:9]:  # Max 9 images
                upload_result = await self._upload_image(client, image_path)
                if upload_result:
                    image_urls.append(upload_result)

        # Add hashtags to content
        post_text = content
        if tags:
            hashtags = " ".join(f"#{tag}#" for tag in tags)
            post_text = f"{content}\n\n{hashtags}"

        payload = {
            "access_token": self.config.access_token,
            "content": post_text[:2000],  # Max 2000 chars
        }

        if image_urls:
            payload["image_list"] = image_urls

        response = await client.post(
            f"{self.CONTENT_API}/micro/publish/",
            json=payload,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("error_code", 0) == 0:
                result_data = data.get("data", {})
                return PublishResult(
                    success=True,
                    post_id=str(result_data.get("item_id", result_data.get("micro_id", ""))),
                    post_url=result_data.get("share_url", ""),
                    platform=self.platform_name,
                    published_at=datetime.utcnow(),
                    raw_response=data,
                )
            else:
                return PublishResult(
                    success=False,
                    error=data.get("message", "Unknown error"),
                    platform=self.platform_name,
                )
        else:
            return PublishResult(
                success=False,
                error=f"HTTP {response.status_code}",
                platform=self.platform_name,
            )

    async def _upload_image(
        self,
        client: Any,
        image_path: str,
    ) -> Optional[str]:
        """Upload an image and return the URL."""
        from pathlib import Path

        path = Path(image_path)
        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                files = {"image": (path.name, f, "image/jpeg")}
                response = await client.post(
                    f"{self.CONTENT_API}/image/upload/",
                    data={"access_token": self.config.access_token},
                    files=files,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error_code", 0) == 0:
                        return data.get("data", {}).get("url", data.get("data", {}).get("web_url"))
        except Exception:
            pass

        return None

    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch trending articles from Toutiao.

        Note: Toutiao's open API has limited search capabilities.
        This fetches hot content or searches public content.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Toutiao",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Toutiao's public API is limited; try to get hot list
                params = {
                    "access_token": self.config.access_token,
                    "count": min(limit, 50),
                }

                if query:
                    params["keyword"] = query

                response = await client.get(
                    f"{self.CONTENT_API}/data/hot_list/",
                    params=params,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error_code", 0) == 0:
                        items = data.get("data", {}).get("hot_list", [])

                        results = []
                        for item in items[:limit]:
                            results.append({
                                "platform": self.platform_name,
                                "post_id": str(item.get("item_id", item.get("id", ""))),
                                "title": item.get("title", ""),
                                "author": item.get("source", item.get("author", "")),
                                "author_id": str(item.get("user_id", "")),
                                "body": item.get("abstract", item.get("content", "")),
                                "likes": item.get("like_count", item.get("digg_count", 0)),
                                "comments": item.get("comment_count", 0),
                                "shares": item.get("share_count", item.get("forward_count", 0)),
                                "views": item.get("read_count", item.get("play_count", 0)),
                                "url": item.get("share_url", item.get("article_url", "")),
                                "published_at": item.get("publish_time", item.get("create_time")),
                            })

                        return FetchResult(
                            success=True,
                            data=results,
                            platform=self.platform_name,
                            fetched_at=datetime.utcnow(),
                        )
                    else:
                        return FetchResult(
                            success=False,
                            error=data.get("message", "Unknown error"),
                            platform=self.platform_name,
                        )
                else:
                    return FetchResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        platform=self.platform_name,
                    )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def fetch_user_posts(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch posts from the authenticated user's account.

        Note: Toutiao API only allows fetching own content.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Toutiao",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.CONTENT_API}/article/list/",
                    params={
                        "access_token": self.config.access_token,
                        "count": min(limit, 50),
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error_code", 0) == 0:
                        items = data.get("data", {}).get("article_list", [])

                        results = []
                        for item in items[:limit]:
                            results.append({
                                "platform": self.platform_name,
                                "post_id": str(item.get("item_id", item.get("article_id", ""))),
                                "title": item.get("title", ""),
                                "author": self._screen_name or "",
                                "author_id": self._user_id or "",
                                "body": item.get("abstract", item.get("content", "")),
                                "likes": item.get("like_count", item.get("digg_count", 0)),
                                "comments": item.get("comment_count", 0),
                                "shares": item.get("share_count", item.get("forward_count", 0)),
                                "views": item.get("read_count", 0),
                                "url": item.get("share_url", item.get("article_url", "")),
                                "published_at": item.get("publish_time", item.get("create_time")),
                                "status": item.get("status", ""),  # published, reviewing, etc.
                            })

                        return FetchResult(
                            success=True,
                            data=results,
                            platform=self.platform_name,
                            fetched_at=datetime.utcnow(),
                        )
                    else:
                        return FetchResult(
                            success=False,
                            error=data.get("message", "Unknown error"),
                            platform=self.platform_name,
                        )
                else:
                    return FetchResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        platform=self.platform_name,
                    )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def get_article_stats(
        self,
        article_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed statistics for an article.

        Args:
            article_id: The article/item ID

        Returns:
            Dictionary with read_count, like_count, comment_count, share_count
        """
        if not self.is_connected():
            return {"error": "Not connected"}

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.CONTENT_API}/article/stats/",
                    params={
                        "access_token": self.config.access_token,
                        "item_id": article_id,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error_code", 0) == 0:
                        return data.get("data", {})

                return {"error": "Failed to fetch stats"}

        except Exception as e:
            return {"error": str(e)}
