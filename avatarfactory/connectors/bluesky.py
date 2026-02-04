"""
Bluesky platform connector.

Bluesky has an open AT Protocol API, making it the simplest platform to integrate.
Documentation: https://docs.bsky.app/
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorConfig,
    FetchResult,
    PublishResult,
    TrendingContent,
)


class BlueskyConnector(BasePlatformConnector):
    """Bluesky platform connector using AT Protocol"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._session: Optional[Dict[str, Any]] = None
        self._did: Optional[str] = None  # Decentralized ID

    @property
    def platform_name(self) -> str:
        return "bluesky"

    async def connect(self) -> bool:
        """Connect to Bluesky using app password authentication"""
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for Bluesky connector. Install with: pip install httpx")

        if not self.config.username or not self.config.password:
            raise ValueError("Bluesky requires username (handle) and password (app password)")

        self.status = ConnectionStatus.CONNECTING

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://bsky.social/xrpc/com.atproto.server.createSession",
                    json={
                        "identifier": self.config.username,
                        "password": self.config.password,
                    },
                )

                if response.status_code == 200:
                    self._session = response.json()
                    self._did = self._session.get("did")
                    self.status = ConnectionStatus.CONNECTED
                    return True
                else:
                    error = response.json().get("message", "Unknown error")
                    raise ValueError(f"Authentication failed: {error}")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to Bluesky: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Bluesky"""
        self._session = None
        self._did = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid"""
        if not self._session:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://bsky.social/xrpc/app.bsky.actor.getProfile",
                    params={"actor": self._did},
                    headers={"Authorization": f"Bearer {self._session.get('accessJwt')}"},
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
        """Publish a post to Bluesky"""
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Bluesky",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build post text with hashtags
            post_text = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags)
                post_text = f"{content}\n\n{hashtags}"

            # Create post record
            now = datetime.utcnow().isoformat() + "Z"
            record = {
                "$type": "app.bsky.feed.post",
                "text": post_text[:300],  # Bluesky limit is 300 chars
                "createdAt": now,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": f"Bearer {self._session.get('accessJwt')}"},
                    json={
                        "repo": self._did,
                        "collection": "app.bsky.feed.post",
                        "record": record,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    uri = data.get("uri", "")
                    # Convert AT URI to web URL
                    # at://did:plc:xxx/app.bsky.feed.post/xxx -> https://bsky.app/profile/xxx/post/xxx
                    parts = uri.split("/")
                    post_id = parts[-1] if parts else ""
                    handle = self.config.username

                    return PublishResult(
                        success=True,
                        post_id=post_id,
                        post_url=f"https://bsky.app/profile/{handle}/post/{post_id}",
                        platform=self.platform_name,
                        published_at=datetime.utcnow(),
                        raw_response=data,
                    )
                else:
                    error = response.json().get("message", "Unknown error")
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
        """Fetch trending/popular posts from Bluesky"""
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Bluesky",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                if query:
                    # Search posts
                    response = await client.get(
                        "https://bsky.social/xrpc/app.bsky.feed.searchPosts",
                        params={"q": query, "limit": min(limit, 100)},
                        headers={"Authorization": f"Bearer {self._session.get('accessJwt')}"},
                    )
                else:
                    # Get popular feed
                    response = await client.get(
                        "https://bsky.social/xrpc/app.bsky.feed.getTimeline",
                        params={"limit": min(limit, 100)},
                        headers={"Authorization": f"Bearer {self._session.get('accessJwt')}"},
                    )

                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("posts", data.get("feed", []))

                    results = []
                    for item in posts[:limit]:
                        post = item.get("post", item) if isinstance(item, dict) else item
                        if not post:
                            continue

                        record = post.get("record", {})
                        author = post.get("author", {})

                        results.append({
                            "platform": self.platform_name,
                            "post_id": post.get("uri", "").split("/")[-1],
                            "author": author.get("handle", ""),
                            "author_id": author.get("did", ""),
                            "body": record.get("text", ""),
                            "likes": post.get("likeCount", 0),
                            "comments": post.get("replyCount", 0),
                            "shares": post.get("repostCount", 0),
                            "published_at": record.get("createdAt"),
                            "url": f"https://bsky.app/profile/{author.get('handle')}/post/{post.get('uri', '').split('/')[-1]}",
                        })

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                        cursor=data.get("cursor"),
                    )
                else:
                    error = response.json().get("message", "Unknown error")
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
        """Fetch posts from a user"""
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Bluesky",
                platform=self.platform_name,
            )

        actor = user_id or self._did

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
                    params={"actor": actor, "limit": min(limit, 100)},
                    headers={"Authorization": f"Bearer {self._session.get('accessJwt')}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    feed = data.get("feed", [])

                    results = []
                    for item in feed[:limit]:
                        post = item.get("post", {})
                        record = post.get("record", {})
                        author = post.get("author", {})

                        results.append({
                            "platform": self.platform_name,
                            "post_id": post.get("uri", "").split("/")[-1],
                            "author": author.get("handle", ""),
                            "author_id": author.get("did", ""),
                            "body": record.get("text", ""),
                            "likes": post.get("likeCount", 0),
                            "comments": post.get("replyCount", 0),
                            "shares": post.get("repostCount", 0),
                            "published_at": record.get("createdAt"),
                        })

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                        cursor=data.get("cursor"),
                    )
                else:
                    error = response.json().get("message", "Unknown error")
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
