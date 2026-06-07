"""
Instagram platform connector.

Instagram uses the Meta Graph API for business accounts.
Documentation: https://developers.facebook.com/docs/instagram-api
"""

from datetime import datetime
from typing import Any, List, Optional

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


@ConnectorRegistry.register_decorator("instagram")
@ConnectorRegistry.register_decorator("ig")
class InstagramConnector(BasePlatformConnector):
    """
    Instagram platform connector using Meta Graph API.

    Required credentials:
    - access_token: Meta Graph API access token
    - instagram_business_account_id: Instagram Business Account ID

    Notes:
    - Only works with Instagram Business or Creator accounts
    - Images must be publicly accessible URLs for publishing
    - Personal accounts are not supported by the API
    """

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._account_id = config.extra.get("instagram_business_account_id")
        self._username: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "instagram"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="instagram",
            display_name="Instagram",
            description="Instagram Business via Meta Graph API",
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
                    env_var="INSTAGRAM_ACCESS_TOKEN",
                ),
                ConnectorConfigField(
                    name="instagram_business_account_id",
                    label="Business Account ID",
                    field_type="text",
                    required=True,
                    description=("Instagram Business or Creator account ID"),
                    env_var="INSTAGRAM_BUSINESS_ACCOUNT_ID",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Requires a Business or"
                " Creator Instagram account with Meta Graph API token."
                " Call connector.publish(content, images) for single-image"
                " or carousel posts (images must be publicly accessible"
                " URLs). No public search API for discovery. Sub-agents"
                " should use this connector through the publish() method"
                " for visual content distribution."
            ),
        )

    async def connect(self) -> bool:
        """Connect to Instagram using Graph API access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Instagram connector. Install with: pip install httpx"
            )

        if not self.config.access_token:
            raise ValueError("Instagram requires access_token from Meta Graph API")

        if not self._account_id:
            raise ValueError(
                "Instagram requires instagram_business_account_id. "
                "Obtain this from the Facebook Graph API."
            )

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/{self._account_id}",
                    params={
                        "fields": "id,username,name,profile_picture_url,followers_count",
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
            raise RuntimeError(f"Failed to connect to Instagram: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Instagram."""
        self._username = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid."""
        if not self.config.access_token or not self._account_id:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/{self._account_id}",
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
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish a post to Instagram.

        Args:
            content: Caption text (max 2200 characters)
            title: Not used for Instagram
            images: Required list of image URLs (must be publicly accessible)
                   Single image for photo, multiple for carousel
            tags: Hashtags to append to caption
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Instagram",
                platform=self.platform_name,
            )

        if not images or len(images) == 0:
            return PublishResult(
                success=False,
                error="Instagram requires at least one image",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build caption with hashtags
            caption = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags)
                caption = f"{content}\n\n{hashtags}"

            async with httpx.AsyncClient() as client:
                if len(images) == 1:
                    # Single image post
                    result = await self._publish_single_image(client, images[0], caption)
                else:
                    # Carousel post (multiple images)
                    result = await self._publish_carousel(client, images, caption)

                return result

        except Exception as e:
            return PublishResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def _publish_single_image(
        self,
        client: Any,
        image_url: str,
        caption: str,
    ) -> PublishResult:
        """Publish a single image post."""
        # Step 1: Create media container
        container_response = await client.post(
            f"{self.API_BASE}/{self._account_id}/media",
            params={
                "image_url": image_url,
                "caption": caption[:2200],
                "access_token": self.config.access_token,
            },
        )

        if container_response.status_code != 200:
            error = (
                container_response.json().get("error", {}).get("message", container_response.text)
            )
            return PublishResult(
                success=False,
                error=f"Failed to create container: {error}",
                platform=self.platform_name,
            )

        container_id = container_response.json().get("id")

        # Step 2: Publish the container
        return await self._publish_container(client, container_id)

    async def _publish_carousel(
        self,
        client: Any,
        images: List[str],
        caption: str,
    ) -> PublishResult:
        """Publish a carousel post with multiple images."""
        # Step 1: Create containers for each image
        children_ids = []
        for image_url in images[:10]:  # Max 10 items in carousel
            response = await client.post(
                f"{self.API_BASE}/{self._account_id}/media",
                params={
                    "image_url": image_url,
                    "is_carousel_item": "true",
                    "access_token": self.config.access_token,
                },
            )

            if response.status_code != 200:
                continue

            children_ids.append(response.json().get("id"))

        if not children_ids:
            return PublishResult(
                success=False,
                error="Failed to create carousel items",
                platform=self.platform_name,
            )

        # Step 2: Create carousel container
        carousel_response = await client.post(
            f"{self.API_BASE}/{self._account_id}/media",
            params={
                "media_type": "CAROUSEL",
                "caption": caption[:2200],
                "children": ",".join(children_ids),
                "access_token": self.config.access_token,
            },
        )

        if carousel_response.status_code != 200:
            error = carousel_response.json().get("error", {}).get("message", carousel_response.text)
            return PublishResult(
                success=False,
                error=f"Failed to create carousel: {error}",
                platform=self.platform_name,
            )

        carousel_id = carousel_response.json().get("id")

        # Step 3: Publish the carousel
        return await self._publish_container(client, carousel_id)

    async def _publish_container(
        self,
        client: Any,
        container_id: str,
    ) -> PublishResult:
        """Publish a media container."""
        response = await client.post(
            f"{self.API_BASE}/{self._account_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self.config.access_token,
            },
        )

        if response.status_code == 200:
            data = response.json()
            post_id = data.get("id", "")

            return PublishResult(
                success=True,
                post_id=post_id,
                post_url=f"https://www.instagram.com/p/{post_id}/",
                platform=self.platform_name,
                published_at=datetime.utcnow(),
                raw_response=data,
            )
        else:
            error = response.json().get("error", {}).get("message", response.text)
            return PublishResult(
                success=False,
                error=error,
                platform=self.platform_name,
            )

    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch trending content.

        Note: Instagram API doesn't provide public search functionality.
        """
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
        Fetch posts from the authenticated account.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Instagram",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/{self._account_id}/media",
                    params={
                        "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
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
                                "author": self._username,
                                "body": post.get("caption", ""),
                                "likes": post.get("like_count", 0),
                                "comments": post.get("comments_count", 0),
                                "url": post.get("permalink"),
                                "media_url": post.get("media_url"),
                                "media_type": post.get("media_type"),
                                "published_at": post.get("timestamp"),
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
