"""
Mastodon platform connector.

Mastodon has a simple REST API that works across any Mastodon instance.
Documentation: https://docs.joinmastodon.org/api/
"""

from datetime import datetime
from pathlib import Path
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


@ConnectorRegistry.register_decorator("mastodon")
class MastodonConnector(BasePlatformConnector):
    """
    Mastodon platform connector.

    Required credentials:
    - access_token: OAuth access token
    - instance_url: Mastodon instance URL (e.g., https://mastodon.social)

    Mastodon is decentralized, so each user may be on a different instance.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._instance_url = (
            config.extra.get("instance_url", "https://mastodon.social").rstrip("/")
        )
        self._account_id: Optional[str] = None
        self._username: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "mastodon"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="mastodon",
            display_name="Mastodon",
            description="Mastodon/Fediverse via ActivityPub API",
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
                    description="Mastodon OAuth access token",
                    env_var="MASTODON_ACCESS_TOKEN",
                ),
                ConnectorConfigField(
                    name="instance_url",
                    label="Instance URL",
                    field_type="url",
                    required=False,
                    description=(
                        "Mastodon instance URL"
                        " (default: mastodon.social)"
                    ),
                    placeholder="https://mastodon.social",
                    env_var="MASTODON_INSTANCE_URL",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Call"
                " connector.fetch_trending() for trending posts/hashtags"
                " on the instance. Call"
                " connector.fetch_user_posts(user_id) for persona"
                " analysis. Call connector.publish(content, images, tags)"
                " to post toots with optional media and visibility"
                " control. Supports search across federated instances for"
                " broad topic discovery."
            ),
        )

    @property
    def api_base(self) -> str:
        """Get the API base URL for this instance."""
        return f"{self._instance_url}/api/v1"

    async def connect(self) -> bool:
        """Connect to Mastodon using OAuth access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Mastodon connector. Install with: pip install httpx"
            )

        if not self.config.access_token:
            raise ValueError("Mastodon requires access_token")

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                # Verify credentials and get account info
                response = await client.get(
                    f"{self.api_base}/accounts/verify_credentials",
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._account_id = data.get("id")
                    self._username = data.get("username")
                    self.status = ConnectionStatus.CONNECTED
                    return True
                else:
                    error = response.json().get("error", response.text)
                    raise ValueError(f"Authentication failed: {error}")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to Mastodon: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Mastodon."""
        self._account_id = None
        self._username = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid."""
        if not self.config.access_token:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/accounts/verify_credentials",
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                    },
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _upload_media(self, client: Any, image_path: str) -> Optional[str]:
        """Upload media and return the media ID."""
        path = Path(image_path)
        if not path.exists():
            return None

        try:
            with open(path, "rb") as f:
                files = {"file": (path.name, f)}
                response = await client.post(
                    f"{self.api_base}/media",
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                    },
                    files=files,
                )

                if response.status_code in (200, 202):
                    return response.json().get("id")
                return None
        except Exception:
            return None

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        visibility: str = "public",
        spoiler_text: Optional[str] = None,
        in_reply_to_id: Optional[str] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish a status (toot) to Mastodon.

        Args:
            content: Status text (max 500 characters on most instances)
            title: Not used for Mastodon
            images: Optional list of image paths (max 4)
            tags: Hashtags to append
            visibility: "public", "unlisted", "private", or "direct"
            spoiler_text: Content warning text
            in_reply_to_id: ID of status to reply to
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Mastodon",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build status text with hashtags
            status_text = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags)
                status_text = f"{content}\n\n{hashtags}"

            async with httpx.AsyncClient() as client:
                # Upload images if provided
                media_ids = []
                if images:
                    for image_path in images[:4]:  # Max 4 images
                        media_id = await self._upload_media(client, image_path)
                        if media_id:
                            media_ids.append(media_id)

                # Build status data
                status_data: Dict[str, Any] = {
                    "status": status_text[:500],  # Standard Mastodon limit
                    "visibility": visibility,
                }

                if media_ids:
                    status_data["media_ids"] = media_ids

                if spoiler_text:
                    status_data["spoiler_text"] = spoiler_text

                if in_reply_to_id:
                    status_data["in_reply_to_id"] = in_reply_to_id

                response = await client.post(
                    f"{self.api_base}/statuses",
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                    },
                    json=status_data,
                )

                if response.status_code == 200:
                    data = response.json()
                    return PublishResult(
                        success=True,
                        post_id=data.get("id", ""),
                        post_url=data.get("url", ""),
                        platform=self.platform_name,
                        published_at=datetime.utcnow(),
                        raw_response=data,
                    )
                else:
                    error = response.json().get("error", response.text)
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
        Fetch trending posts or search results.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Mastodon",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                if query:
                    # Search statuses
                    response = await client.get(
                        f"{self._instance_url}/api/v2/search",
                        params={
                            "q": query,
                            "type": "statuses",
                            "limit": min(limit, 40),
                        },
                        headers={
                            "Authorization": f"Bearer {self.config.access_token}",
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        statuses = data.get("statuses", [])
                    else:
                        return FetchResult(
                            success=False,
                            error=response.json().get("error", response.text),
                            platform=self.platform_name,
                        )
                else:
                    # Get trending statuses
                    response = await client.get(
                        f"{self.api_base}/trends/statuses",
                        params={"limit": min(limit, 40)},
                        headers={
                            "Authorization": f"Bearer {self.config.access_token}",
                        },
                    )

                    if response.status_code == 200:
                        statuses = response.json()
                    else:
                        # Fall back to public timeline if trends not available
                        response = await client.get(
                            f"{self.api_base}/timelines/public",
                            params={"limit": min(limit, 40)},
                            headers={
                                "Authorization": f"Bearer {self.config.access_token}",
                            },
                        )
                        statuses = response.json() if response.status_code == 200 else []

                results = []
                for status in statuses[:limit]:
                    account = status.get("account", {})
                    results.append({
                        "platform": self.platform_name,
                        "post_id": status.get("id", ""),
                        "author": account.get("username", ""),
                        "author_id": account.get("id", ""),
                        "body": status.get("content", ""),  # HTML content
                        "likes": status.get("favourites_count", 0),
                        "comments": status.get("replies_count", 0),
                        "shares": status.get("reblogs_count", 0),
                        "url": status.get("url"),
                        "published_at": status.get("created_at"),
                        "visibility": status.get("visibility"),
                    })

                return FetchResult(
                    success=True,
                    data=results,
                    platform=self.platform_name,
                    fetched_at=datetime.utcnow(),
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
        Fetch statuses from a user or the authenticated user.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Mastodon",
                platform=self.platform_name,
            )

        try:
            import httpx

            target_id = user_id or self._account_id

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/accounts/{target_id}/statuses",
                    params={
                        "limit": min(limit, 40),
                        "exclude_replies": kwargs.get("exclude_replies", True),
                        "exclude_reblogs": kwargs.get("exclude_reblogs", True),
                    },
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                    },
                )

                if response.status_code == 200:
                    statuses = response.json()

                    results = []
                    for status in statuses[:limit]:
                        account = status.get("account", {})
                        results.append({
                            "platform": self.platform_name,
                            "post_id": status.get("id", ""),
                            "author": account.get("username", ""),
                            "author_id": account.get("id", ""),
                            "body": status.get("content", ""),
                            "likes": status.get("favourites_count", 0),
                            "comments": status.get("replies_count", 0),
                            "shares": status.get("reblogs_count", 0),
                            "url": status.get("url"),
                            "published_at": status.get("created_at"),
                        })

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                    )
                else:
                    error = response.json().get("error", response.text)
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
