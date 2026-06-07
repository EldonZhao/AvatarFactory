"""
Threads (Meta) platform connector.

Threads uses the Meta Graph API similar to Instagram.
Documentation: https://developers.facebook.com/docs/threads
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


@ConnectorRegistry.register_decorator("threads")
class ThreadsConnector(BasePlatformConnector):
    """
    Threads platform connector using Meta Graph API.

    Required credentials:
    - access_token: Meta/Threads API access token
    - user_id: Threads user ID (obtained during OAuth)

    The access token must have threads_basic and threads_content_publish scopes.
    """

    API_BASE = "https://graph.threads.net/v1.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._user_id = config.extra.get("user_id")
        self._username: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "threads"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="threads",
            display_name="Threads",
            description="Meta Threads via Instagram Graph API",
            supports_topic_discovery=False,
            supports_persona_discovery=False,
            supports_publishing=True,
            supports_fetching=False,
            config_fields=[
                ConnectorConfigField(
                    name="access_token",
                    label="Access Token",
                    field_type="password",
                    required=True,
                    description="Meta Graph API access token",
                    env_var="THREADS_ACCESS_TOKEN",
                ),
                ConnectorConfigField(
                    name="user_id",
                    label="User ID",
                    field_type="text",
                    required=False,
                    description="Threads user ID (from Graph API)",
                    env_var="THREADS_USER_ID",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Requires Meta Graph API"
                " access token. Call connector.publish(content) for text"
                " posts, with optional image parameter. Content discovery"
                " is very limited (no public search API). Best used for"
                " content publishing only. Sub-agents can use this"
                " connector through the publish() method for cross-platform"
                " distribution."
            ),
        )

    async def connect(self) -> bool:
        """Connect to Threads using access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Threads connector. Install with: pip install httpx"
            )

        if not self.config.access_token:
            raise ValueError("Threads requires access_token from Meta Graph API")

        if not self._user_id:
            raise ValueError("Threads requires user_id. Obtain this during OAuth flow.")

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                # Verify token by fetching user profile
                response = await client.get(
                    f"{self.API_BASE}/{self._user_id}",
                    params={
                        "fields": "id,username,name,threads_profile_picture_url",
                        "access_token": self.config.access_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._username = data.get("username")
                    self.status = ConnectionStatus.CONNECTED
                    return True
                else:
                    error = response.json().get("error", {}).get("message", response.text)
                    raise ValueError(f"Authentication failed: {error}")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to Threads: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Threads."""
        self._username = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid."""
        if not self.config.access_token or not self._user_id:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/{self._user_id}",
                    params={
                        "access_token": self.config.access_token,
                    },
                )
                return response.status_code == 200
        except Exception:
            return False

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish a post to Threads.

        Args:
            content: Post text (max 500 characters)
            title: Not used for Threads
            images: Optional list of image URLs (must be publicly accessible)
            tags: Hashtags to append
            reply_to: Optional post ID to reply to
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Threads",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build post text with hashtags
            post_text = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags)
                post_text = f"{content}\n\n{hashtags}"

            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                container_params: Dict[str, Any] = {
                    "text": post_text[:500],  # Threads limit
                    "access_token": self.config.access_token,
                }

                if images and len(images) > 0:
                    container_params["media_type"] = "IMAGE"
                    container_params["image_url"] = images[0]  # First image only
                else:
                    container_params["media_type"] = "TEXT"

                if reply_to:
                    container_params["reply_to_id"] = reply_to

                container_response = await client.post(
                    f"{self.API_BASE}/{self._user_id}/threads",
                    params=container_params,
                )

                if container_response.status_code != 200:
                    error = (
                        container_response.json()
                        .get("error", {})
                        .get("message", container_response.text)
                    )
                    return PublishResult(
                        success=False,
                        error=f"Failed to create container: {error}",
                        platform=self.platform_name,
                    )

                container_id = container_response.json().get("id")

                # Step 2: Publish the container
                publish_response = await client.post(
                    f"{self.API_BASE}/{self._user_id}/threads_publish",
                    params={
                        "creation_id": container_id,
                        "access_token": self.config.access_token,
                    },
                )

                if publish_response.status_code == 200:
                    data = publish_response.json()
                    post_id = data.get("id", "")

                    return PublishResult(
                        success=True,
                        post_id=post_id,
                        post_url=f"https://www.threads.net/@{self._username}/post/{post_id}",
                        platform=self.platform_name,
                        published_at=datetime.utcnow(),
                        raw_response=data,
                    )
                else:
                    error = (
                        publish_response.json()
                        .get("error", {})
                        .get("message", publish_response.text)
                    )
                    return PublishResult(
                        success=False,
                        error=error,
                        platform=self.platform_name,
                    )

        except Exception as e:
            return PublishResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch posts from Threads.

        Note: Threads API has limited search capabilities.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Threads",
                platform=self.platform_name,
            )

        # Threads API currently has limited search functionality
        return FetchResult(
            success=True,
            data=[],
            platform=self.platform_name,
            fetched_at=datetime.utcnow(),
        )

    async def fetch_user_posts(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch posts from a user or the authenticated user.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Threads",
                platform=self.platform_name,
            )

        try:
            import httpx

            target_user = user_id or self._user_id

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/{target_user}/threads",
                    params={
                        "fields": "id,text,timestamp,media_type,permalink,like_count,reply_count",
                        "limit": min(limit, 50),
                        "access_token": self.config.access_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("data", [])

                    results = []
                    for post in posts[:limit]:
                        results.append(
                            {
                                "platform": self.platform_name,
                                "post_id": post.get("id", ""),
                                "author": target_user,
                                "body": post.get("text", ""),
                                "likes": post.get("like_count", 0),
                                "comments": post.get("reply_count", 0),
                                "url": post.get("permalink"),
                                "published_at": post.get("timestamp"),
                                "media_type": post.get("media_type"),
                            }
                        )

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                        cursor=data.get("paging", {}).get("cursors", {}).get("after"),
                    )
                else:
                    error = response.json().get("error", {}).get("message", response.text)
                    return FetchResult(
                        success=False,
                        error=error,
                        platform=self.platform_name,
                    )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )
