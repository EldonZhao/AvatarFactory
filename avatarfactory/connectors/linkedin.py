"""
LinkedIn platform connector.

LinkedIn uses OAuth 2.0 with specific scopes for posting content.
Documentation: https://learn.microsoft.com/en-us/linkedin/
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


@ConnectorRegistry.register_decorator("linkedin")
class LinkedInConnector(BasePlatformConnector):
    """
    LinkedIn platform connector using OAuth 2.0.

    Required credentials:
    - client_id: LinkedIn App Client ID
    - client_secret: LinkedIn App Client Secret
    - access_token: OAuth 2.0 access token

    Optional:
    - organization_id: For posting as a company page
    """

    API_BASE = "https://api.linkedin.com/v2"
    SHARE_API = "https://api.linkedin.com/v2/ugcPosts"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._member_id: Optional[str] = None
        self._organization_id = config.extra.get("organization_id")

    @property
    def platform_name(self) -> str:
        return "linkedin"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="linkedin",
            display_name="LinkedIn",
            description="LinkedIn professional network via OAuth 2.0",
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
                    description="OAuth 2.0 access token from LinkedIn",
                    env_var="LINKEDIN_ACCESS_TOKEN",
                ),
                ConnectorConfigField(
                    name="client_id",
                    label="Client ID",
                    field_type="text",
                    required=False,
                    description=("LinkedIn App Client ID (for OAuth flow)"),
                    env_var="LINKEDIN_CLIENT_ID",
                ),
                ConnectorConfigField(
                    name="client_secret",
                    label="Client Secret",
                    field_type="password",
                    required=False,
                    description=("LinkedIn App Client Secret (for OAuth flow)"),
                    env_var="LINKEDIN_CLIENT_SECRET",
                ),
                ConnectorConfigField(
                    name="organization_id",
                    label="Organization ID",
                    field_type="text",
                    required=False,
                    description=("LinkedIn Company Page ID" " (for posting as organization)"),
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Requires OAuth 2.0 access"
                " token. Call connector.publish(content) to share posts on"
                " LinkedIn. Fetching trending content is very limited due"
                " to LinkedIn API restrictions (partner-only). Best used"
                " for professional content publishing only. Sub-agents"
                " should use this connector primarily through the"
                " publish() method."
            ),
        )

    async def connect(self) -> bool:
        """Connect to LinkedIn using OAuth access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for LinkedIn connector. Install with: pip install httpx"
            )

        if not self.config.access_token:
            raise ValueError("LinkedIn requires access_token. " "Use OAuth 2.0 flow to obtain one.")

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                # Get the authenticated user's profile
                response = await client.get(
                    f"{self.API_BASE}/userinfo",
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._member_id = data.get("sub")
                    self.status = ConnectionStatus.CONNECTED
                    return True
                else:
                    error = response.json().get("message", response.text)
                    raise ValueError(f"Authentication failed: {error}")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to LinkedIn: {e}")

    async def disconnect(self) -> None:
        """Disconnect from LinkedIn."""
        self._member_id = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid."""
        if not self.config.access_token:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/userinfo",
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
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
        visibility: str = "PUBLIC",
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish a post to LinkedIn.

        Args:
            content: Post text
            title: Optional title (for articles)
            images: Optional list of image paths (not yet supported)
            tags: Hashtags to append
            visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN"
            **kwargs: Additional options
                - as_organization: bool - Post as organization if configured
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to LinkedIn",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build post text with hashtags
            post_text = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags)
                post_text = f"{content}\n\n{hashtags}"

            # Determine author (person or organization)
            as_organization = kwargs.get("as_organization", False)
            if as_organization and self._organization_id:
                author = f"urn:li:organization:{self._organization_id}"
            else:
                author = f"urn:li:person:{self._member_id}"

            # Build UGC post
            post_data = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": post_text[:3000],  # LinkedIn limit
                        },
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility,
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.SHARE_API,
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=post_data,
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    post_id = data.get("id", "")

                    return PublishResult(
                        success=True,
                        post_id=post_id,
                        post_url=f"https://www.linkedin.com/feed/update/{post_id}",
                        platform=self.platform_name,
                        published_at=datetime.utcnow(),
                        raw_response=data,
                    )
                else:
                    error = response.json().get("message", response.text)
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
        Fetch posts from LinkedIn feed.

        Note: LinkedIn API has limited search capabilities for non-partner apps.
        This fetches the authenticated user's feed.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to LinkedIn",
                platform=self.platform_name,
            )

        # LinkedIn's content search API is restricted
        # Return a placeholder indicating limited functionality
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

        Note: LinkedIn API access to user posts is limited for non-partner apps.
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to LinkedIn",
                platform=self.platform_name,
            )

        try:
            import httpx

            author = user_id or f"urn:li:person:{self._member_id}"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/ugcPosts",
                    params={
                        "q": "authors",
                        "authors": f"List({author})",
                        "count": min(limit, 50),
                    },
                    headers={
                        "Authorization": f"Bearer {self.config.access_token}",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    elements = data.get("elements", [])

                    results = []
                    for post in elements[:limit]:
                        specific = post.get("specificContent", {})
                        share_content = specific.get("com.linkedin.ugc.ShareContent", {})
                        commentary = share_content.get("shareCommentary", {})

                        results.append(
                            {
                                "platform": self.platform_name,
                                "post_id": post.get("id", ""),
                                "author": post.get("author", ""),
                                "body": commentary.get("text", ""),
                                "published_at": post.get("created", {}).get("time"),
                            }
                        )

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                    )
                else:
                    error = response.json().get("message", response.text)
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
