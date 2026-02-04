"""
Bluesky platform connector.

Bluesky has an open AT Protocol API, making it the simplest platform to integrate.
Documentation: https://docs.bsky.app/
"""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorConfig,
    FetchResult,
    PublishResult,
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

    async def _upload_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Upload an image to Bluesky blob storage.

        Args:
            image_path: Local file path or URL to image

        Returns:
            Blob reference dict with $link and mimeType, or None on failure
        """
        try:
            import httpx

            # Read image file
            path = Path(image_path)
            if not path.exists():
                return None

            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type or not mime_type.startswith("image/"):
                mime_type = "image/jpeg"  # Default fallback

            with open(path, "rb") as f:
                image_data = f.read()

            # Upload to Bluesky
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                    headers={
                        "Authorization": f"Bearer {self._session.get('accessJwt')}",
                        "Content-Type": mime_type,
                    },
                    content=image_data,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("blob")
                else:
                    return None

        except Exception:
            return None

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        alt_texts: Optional[List[str]] = None,
        reply_to: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish a post to Bluesky with optional images.

        Args:
            content: Post text (max 300 chars)
            title: Not used for Bluesky
            images: List of image file paths (max 4)
            tags: Hashtags to append
            alt_texts: Alt text for each image
            reply_to: Reply reference dict with 'uri' and 'cid' of parent post
        """
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
            record: Dict[str, Any] = {
                "$type": "app.bsky.feed.post",
                "text": post_text[:300],  # Bluesky limit is 300 chars
                "createdAt": now,
            }

            # Add reply reference if this is a reply
            if reply_to and reply_to.get("uri") and reply_to.get("cid"):
                # For a thread, we need both root and parent references
                root = reply_to.get("root", reply_to)  # First post is root
                record["reply"] = {
                    "root": {
                        "uri": root.get("uri"),
                        "cid": root.get("cid"),
                    },
                    "parent": {
                        "uri": reply_to.get("uri"),
                        "cid": reply_to.get("cid"),
                    },
                }

            # Upload and attach images if provided
            if images:
                uploaded_images = []
                for i, image_path in enumerate(images[:4]):  # Max 4 images
                    blob = await self._upload_image(image_path)
                    if blob:
                        alt_text = ""
                        if alt_texts and i < len(alt_texts):
                            alt_text = alt_texts[i]
                        uploaded_images.append({
                            "alt": alt_text,
                            "image": blob,
                        })

                if uploaded_images:
                    record["embed"] = {
                        "$type": "app.bsky.embed.images",
                        "images": uploaded_images,
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
                    cid = data.get("cid", "")
                    parts = uri.split("/")
                    post_id = parts[-1] if parts else ""
                    handle = self.config.username

                    return PublishResult(
                        success=True,
                        post_id=post_id,
                        post_url=f"https://bsky.app/profile/{handle}/post/{post_id}",
                        platform=self.platform_name,
                        published_at=datetime.utcnow(),
                        raw_response={"uri": uri, "cid": cid, **data},
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

    async def publish_thread(
        self,
        posts: List[str],
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PublishResult]:
        """
        Publish a thread of connected posts.

        Args:
            posts: List of post texts (each max 300 chars)
            images: Images to attach to first post only
            tags: Tags (usually already in last post text)

        Returns:
            List of PublishResult for each post in thread
        """
        if not self.is_connected():
            return [PublishResult(
                success=False,
                error="Not connected to Bluesky",
                platform=self.platform_name,
            )]

        results = []
        root_ref = None  # Reference to first post (thread root)
        parent_ref = None  # Reference to previous post

        for i, post_text in enumerate(posts):
            # Only attach images to first post
            post_images = images if i == 0 else None

            # Build reply reference for posts after the first
            reply_to = None
            if parent_ref:
                reply_to = {
                    "uri": parent_ref["uri"],
                    "cid": parent_ref["cid"],
                    "root": root_ref,  # Always reference the root
                }

            result = await self.publish(
                content=post_text,
                images=post_images,
                reply_to=reply_to,
            )

            results.append(result)

            if not result.success:
                # Stop on first failure
                break

            # Extract uri and cid for next post's reply reference
            raw = result.raw_response or {}
            current_ref = {
                "uri": raw.get("uri"),
                "cid": raw.get("cid"),
            }

            # First post becomes the root
            if i == 0:
                root_ref = current_ref

            # Current post becomes parent for next post
            parent_ref = current_ref

        return results

    def _extract_images_from_embed(self, embed: Dict[str, Any]) -> List[str]:
        """Extract image URLs from post embed."""
        images = []
        embed_type = embed.get("$type", "")

        if embed_type == "app.bsky.embed.images#view":
            for img in embed.get("images", []):
                if "fullsize" in img:
                    images.append(img["fullsize"])
                elif "thumb" in img:
                    images.append(img["thumb"])
        elif embed_type == "app.bsky.embed.images":
            # Record format (not view format)
            for img in embed.get("images", []):
                if "image" in img and "$link" in img["image"]:
                    # This is a blob reference, not a URL
                    pass

        return images

    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """Fetch trending/popular posts from Bluesky with image information"""
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
                    response = await client.get(
                        "https://bsky.social/xrpc/app.bsky.feed.searchPosts",
                        params={"q": query, "limit": min(limit, 100)},
                        headers={"Authorization": f"Bearer {self._session.get('accessJwt')}"},
                    )
                else:
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
                        embed = post.get("embed", {})

                        # Extract images from embed
                        images = self._extract_images_from_embed(embed)
                        has_media = len(images) > 0 or "$type" in embed

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
                            # Image information
                            "images": images,
                            "image_count": len(images),
                            "has_media": has_media,
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
                        embed = post.get("embed", {})

                        images = self._extract_images_from_embed(embed)

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
                            "images": images,
                            "image_count": len(images),
                            "has_media": len(images) > 0,
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
