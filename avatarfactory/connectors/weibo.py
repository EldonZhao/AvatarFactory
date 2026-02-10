"""
Weibo (微博) platform connector.

Weibo uses OAuth 2.0 for authentication.
Documentation: https://open.weibo.com/wiki/
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorConfig,
    FetchResult,
    PublishResult,
)
from avatarfactory.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register_decorator("weibo")
class WeiboConnector(BasePlatformConnector):
    """
    Weibo platform connector using OAuth 2.0.

    Required credentials:
    - access_token: OAuth 2.0 access token
    - uid: User ID (obtained during OAuth flow)

    Optional:
    - app_key: Weibo App Key (for certain API calls)
    """

    API_BASE = "https://api.weibo.com/2"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._uid = config.extra.get("uid")
        self._screen_name: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "weibo"

    async def connect(self) -> bool:
        """Connect to Weibo using OAuth access token."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Weibo connector. Install with: pip install httpx"
            )

        if not self.config.access_token:
            raise ValueError("Weibo requires access_token from OAuth 2.0 flow")

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                # Get token info and user ID
                response = await client.get(
                    f"{self.API_BASE}/account/get_uid.json",
                    params={
                        "access_token": self.config.access_token,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self._uid = str(data.get("uid"))

                    # Get user profile
                    profile_response = await client.get(
                        f"{self.API_BASE}/users/show.json",
                        params={
                            "access_token": self.config.access_token,
                            "uid": self._uid,
                        },
                    )

                    if profile_response.status_code == 200:
                        profile = profile_response.json()
                        self._screen_name = profile.get("screen_name")

                    self.status = ConnectionStatus.CONNECTED
                    return True
                else:
                    error = response.json().get("error", response.text)
                    raise ValueError(f"Authentication failed: {error}")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to Weibo: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Weibo."""
        self._screen_name = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid."""
        if not self.config.access_token:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/account/get_uid.json",
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
        Publish a post (微博) to Weibo.

        Args:
            content: Post text (max 2000 characters)
            title: Not used for Weibo
            images: Optional list of image paths (up to 9 images)
            tags: Hashtags to append (wrapped in #tag#)
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Weibo",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build post text with hashtags (Weibo uses #tag# format)
            post_text = content
            if tags:
                hashtags = " ".join(f"#{tag}#" for tag in tags)
                post_text = f"{content}\n\n{hashtags}"

            async with httpx.AsyncClient() as client:
                if images and len(images) > 0:
                    # Post with images
                    result = await self._publish_with_images(
                        client, post_text, images
                    )
                else:
                    # Text-only post
                    response = await client.post(
                        f"{self.API_BASE}/statuses/share.json",
                        data={
                            "access_token": self.config.access_token,
                            "status": post_text[:2000],
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return PublishResult(
                            success=True,
                            post_id=str(data.get("id", "")),
                            post_url=f"https://weibo.com/{self._uid}/{data.get('mid', '')}",
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

                return result

        except Exception as e:
            return PublishResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def _publish_with_images(
        self,
        client: Any,
        text: str,
        images: List[str],
    ) -> PublishResult:
        """Publish a post with images."""
        from pathlib import Path

        # Upload images and get pic_ids
        pic_ids = []
        for image_path in images[:9]:  # Weibo allows up to 9 images
            path = Path(image_path)
            if not path.exists():
                continue

            with open(path, "rb") as f:
                files = {"pic": (path.name, f)}
                response = await client.post(
                    "https://api.weibo.com/2/statuses/upload_pic.json",
                    data={"access_token": self.config.access_token},
                    files=files,
                )

                if response.status_code == 200:
                    pic_ids.append(response.json().get("pic_id"))

        if not pic_ids:
            # Fall back to text-only if image upload failed
            response = await client.post(
                f"{self.API_BASE}/statuses/share.json",
                data={
                    "access_token": self.config.access_token,
                    "status": text[:2000],
                },
            )
        else:
            # Post with uploaded images
            response = await client.post(
                f"{self.API_BASE}/statuses/share.json",
                data={
                    "access_token": self.config.access_token,
                    "status": text[:2000],
                    "pic_id": ",".join(pic_ids),
                },
            )

        if response.status_code == 200:
            data = response.json()
            return PublishResult(
                success=True,
                post_id=str(data.get("id", "")),
                post_url=f"https://weibo.com/{self._uid}/{data.get('mid', '')}",
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
                error="Not connected to Weibo",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                if query:
                    # Search posts
                    response = await client.get(
                        f"{self.API_BASE}/search/topics.json",
                        params={
                            "access_token": self.config.access_token,
                            "q": query,
                            "count": min(limit, 50),
                        },
                    )
                else:
                    # Get public timeline (hot posts)
                    response = await client.get(
                        f"{self.API_BASE}/statuses/public_timeline.json",
                        params={
                            "access_token": self.config.access_token,
                            "count": min(limit, 50),
                        },
                    )

                if response.status_code == 200:
                    data = response.json()
                    statuses = data.get("statuses", data.get("topics", []))

                    results = []
                    for status in statuses[:limit]:
                        user = status.get("user", {})
                        results.append({
                            "platform": self.platform_name,
                            "post_id": str(status.get("id", "")),
                            "author": user.get("screen_name", ""),
                            "author_id": str(user.get("id", "")),
                            "body": status.get("text", ""),
                            "likes": status.get("attitudes_count", 0),
                            "comments": status.get("comments_count", 0),
                            "shares": status.get("reposts_count", 0),
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
                error="Not connected to Weibo",
                platform=self.platform_name,
            )

        try:
            import httpx

            target_uid = user_id or self._uid

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/statuses/user_timeline.json",
                    params={
                        "access_token": self.config.access_token,
                        "uid": target_uid,
                        "count": min(limit, 50),
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    statuses = data.get("statuses", [])

                    results = []
                    for status in statuses[:limit]:
                        user = status.get("user", {})
                        results.append({
                            "platform": self.platform_name,
                            "post_id": str(status.get("id", "")),
                            "author": user.get("screen_name", ""),
                            "author_id": str(user.get("id", "")),
                            "body": status.get("text", ""),
                            "likes": status.get("attitudes_count", 0),
                            "comments": status.get("comments_count", 0),
                            "shares": status.get("reposts_count", 0),
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
