"""
Xiaohongshu (小红书) platform connector.

Xiaohongshu does not have an official public API, so this connector uses
cookie-based authentication and web API endpoints.

IMPORTANT: This connector is for personal/educational use. Always respect
Xiaohongshu's Terms of Service and rate limits.
"""

import hashlib
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CookieExpiredError(Exception):
    """Raised when the Xiaohongshu cookie has expired."""
    pass


class CookieExpiringWarning(Warning):
    """Warning when the cookie is about to expire."""
    pass

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorConfig,
    FetchResult,
    PublishResult,
)


class XiaohongshuConnector(BasePlatformConnector):
    """
    Xiaohongshu platform connector using cookie-based authentication.

    Configuration:
        - cookie: Full cookie string from browser (required)
        - user_id: Your Xiaohongshu user ID (optional, for fetching own posts)

    Example:
        config = ConnectorConfig(
            extra={
                "cookie": "your_cookie_string",
                "user_id": "your_user_id",
            }
        )
        connector = XiaohongshuConnector(config)
    """

    BASE_URL = "https://edith.xiaohongshu.com"
    WEB_URL = "https://www.xiaohongshu.com"

    # Cookie expiration settings
    COOKIE_WARNING_DAYS = 3  # Warn when cookie might expire within this many days
    COOKIE_CHECK_INTERVAL = 3600  # Check cookie status every hour (seconds)

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._cookie: Optional[str] = None
        self._user_id: Optional[str] = None
        self._headers: Dict[str, str] = {}
        self._last_cookie_check: Optional[datetime] = None
        self._cookie_valid: bool = False
        self._consecutive_failures: int = 0

    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

    def _generate_x_s(self, url: str, data: Optional[str] = None) -> str:
        """
        Generate X-s signature for API requests.

        Note: This is a simplified version. The actual XHS signature
        algorithm is more complex and changes frequently.
        """
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
        sign_str = f"{url}{data or ''}{timestamp}{random_str}"
        return hashlib.md5(sign_str.encode()).hexdigest()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with cookie and common fields."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": self._cookie or "",
            "Origin": self.WEB_URL,
            "Referer": f"{self.WEB_URL}/",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def connect(self) -> bool:
        """
        Connect to Xiaohongshu using cookie authentication.

        The cookie should be obtained from your browser after logging in.
        """
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for Xiaohongshu connector. Install with: pip install httpx")

        # Get cookie from config
        self._cookie = self.config.extra.get("cookie") or self.config.extra.get("cookies")
        self._user_id = self.config.extra.get("user_id")

        if not self._cookie:
            raise ValueError(
                "Xiaohongshu requires cookie authentication. "
                "Set cookie in config.extra['cookie']"
            )

        self.status = ConnectionStatus.CONNECTING
        self._headers = self._build_headers()

        # Verify connection by fetching user info
        if await self.verify_credentials():
            self.status = ConnectionStatus.CONNECTED
            return True
        else:
            self.status = ConnectionStatus.ERROR
            raise ValueError("Cookie authentication failed. Please check your cookie.")

    async def disconnect(self) -> None:
        """Disconnect from Xiaohongshu."""
        self._cookie = None
        self._headers = {}
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify that the cookie is valid by checking user info."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Try to fetch user info to verify cookie
                response = await client.get(
                    f"{self.BASE_URL}/api/sns/web/v1/user/selfinfo",
                    headers=self._headers,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") or data.get("code") == 0:
                        # Extract user ID if available
                        user_info = data.get("data", {})
                        if user_info.get("user_id"):
                            self._user_id = user_info["user_id"]
                        self._cookie_valid = True
                        self._consecutive_failures = 0
                        self._last_cookie_check = datetime.now()
                        return True

                # Check for specific error codes indicating expired cookie
                if response.status_code == 401:
                    self._cookie_valid = False
                    raise CookieExpiredError(
                        "Cookie has expired. Please update XIAOHONGSHU_COOKIE in your .env file.\n"
                        "Steps: 1) Login to xiaohongshu.com 2) Open DevTools (F12) 3) Copy cookie from Network tab"
                    )

                return False

        except CookieExpiredError:
            raise
        except Exception:
            return False

    async def check_cookie_status(self) -> Tuple[bool, Optional[str]]:
        """
        Check if the cookie is still valid and return status with message.

        Returns:
            Tuple of (is_valid, warning_message)
            - is_valid: True if cookie is working
            - warning_message: Warning string if cookie might expire soon, None otherwise
        """
        # Skip check if we checked recently
        if self._last_cookie_check:
            elapsed = (datetime.now() - self._last_cookie_check).total_seconds()
            if elapsed < self.COOKIE_CHECK_INTERVAL and self._cookie_valid:
                return (True, None)

        try:
            is_valid = await self.verify_credentials()

            if not is_valid:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    return (False, "Cookie appears to be expired or invalid. Please refresh your cookie.")
                return (False, f"Cookie check failed ({self._consecutive_failures}/3 attempts)")

            # Cookie is valid - check for potential expiration warning
            warning = self._check_cookie_expiration_warning()
            return (True, warning)

        except CookieExpiredError as e:
            return (False, str(e))
        except Exception as e:
            return (False, f"Error checking cookie: {e}")

    def _check_cookie_expiration_warning(self) -> Optional[str]:
        """
        Analyze cookie to detect potential expiration.

        Returns warning message if cookie might expire soon, None otherwise.
        """
        if not self._cookie:
            return None

        # Try to parse cookie expiration from common cookie fields
        # Note: Most session cookies don't have explicit expiration in the string
        # This is a heuristic based on cookie age tracking

        # Check for timestamp-based cookies that XHS might use
        import re

        # Look for timestamp patterns in cookie (some cookies embed creation time)
        timestamp_patterns = [
            r'timestamp=(\d+)',
            r'_ts=(\d+)',
            r'create_time=(\d+)',
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, self._cookie)
            if match:
                try:
                    ts = int(match.group(1))
                    # Handle milliseconds
                    if ts > 1e12:
                        ts = ts / 1000
                    cookie_time = datetime.fromtimestamp(ts)
                    age = datetime.now() - cookie_time

                    # Warn if cookie is older than 25 days (assuming ~30 day expiry)
                    if age.days >= 25:
                        days_remaining = max(0, 30 - age.days)
                        return (
                            f"⚠️ Cookie is {age.days} days old and may expire soon "
                            f"(~{days_remaining} days remaining). Consider refreshing."
                        )
                except (ValueError, OSError):
                    pass

        return None

    async def ensure_valid_cookie(self) -> None:
        """
        Ensure cookie is valid before making requests.
        Raises CookieExpiredError if cookie is expired.
        """
        is_valid, message = await self.check_cookie_status()

        if not is_valid:
            self.status = ConnectionStatus.ERROR
            raise CookieExpiredError(
                message or "Cookie has expired. Please update XIAOHONGSHU_COOKIE."
            )

        if message:
            # Log warning but don't fail
            import warnings
            warnings.warn(message, CookieExpiringWarning)

    def get_cookie_refresh_instructions(self) -> str:
        """Return instructions for refreshing the cookie."""
        return """
╔══════════════════════════════════════════════════════════════════╗
║           如何刷新小红书 Cookie (How to Refresh Cookie)           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  1. 打开浏览器，访问 https://www.xiaohongshu.com                   ║
║  2. 登录你的账号                                                  ║
║  3. 按 F12 打开开发者工具                                         ║
║  4. 切换到 Network (网络) 标签页                                   ║
║  5. 刷新页面，点击任意一个请求                                      ║
║  6. 在 Headers 中找到 Cookie 字段                                 ║
║  7. 复制完整的 Cookie 值                                          ║
║  8. 更新 .env 文件中的 XIAOHONGSHU_COOKIE                         ║
║                                                                  ║
║  Cookie 通常有效期为 7-30 天                                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""

    async def _upload_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Upload an image to Xiaohongshu.

        Args:
            image_path: Local file path to image

        Returns:
            Image info dict with file_id, or None on failure
        """
        try:
            import httpx

            path = Path(image_path)
            if not path.exists():
                return None

            # Read image file
            with open(path, "rb") as f:
                image_data = f.read()

            # Determine content type
            content_type = "image/jpeg"
            if path.suffix.lower() == ".png":
                content_type = "image/png"
            elif path.suffix.lower() == ".gif":
                content_type = "image/gif"
            elif path.suffix.lower() == ".webp":
                content_type = "image/webp"

            # Get upload URL first
            async with httpx.AsyncClient() as client:
                # Request upload token
                token_response = await client.post(
                    f"{self.BASE_URL}/api/sns/web/v1/upload/token",
                    headers=self._headers,
                    json={"file_count": 1, "source": "web"},
                    timeout=30.0,
                )

                if token_response.status_code != 200:
                    return None

                token_data = token_response.json()
                if not token_data.get("success"):
                    return None

                upload_info = token_data.get("data", {}).get("upload_temp_permits", [{}])[0]
                upload_url = upload_info.get("upload_url")
                file_id = upload_info.get("file_id")

                if not upload_url:
                    return None

                # Upload image
                upload_response = await client.put(
                    upload_url,
                    content=image_data,
                    headers={
                        "Content-Type": content_type,
                    },
                    timeout=60.0,
                )

                if upload_response.status_code in (200, 201):
                    return {
                        "file_id": file_id,
                        "width": 0,  # Would need to read from image
                        "height": 0,
                    }

                return None

        except Exception:
            return None

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish a note to Xiaohongshu.

        Args:
            content: Note content (body text)
            title: Note title (required, max 20 chars)
            images: List of image file paths (required, 1-9 images)
            tags: Hashtags to include

        Note:
            Xiaohongshu requires at least one image for note publishing.
            Title is also required (max 20 characters).
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

        # Check cookie validity before publishing
        try:
            await self.ensure_valid_cookie()
        except CookieExpiredError as e:
            return PublishResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

        if not images:
            return PublishResult(
                success=False,
                error="Xiaohongshu requires at least one image",
                platform=self.platform_name,
            )

        if not title:
            return PublishResult(
                success=False,
                error="Xiaohongshu requires a title",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Upload images first
            uploaded_images = []
            for image_path in images[:9]:  # Max 9 images
                image_info = await self._upload_image(image_path)
                if image_info:
                    uploaded_images.append(image_info)

            if not uploaded_images:
                return PublishResult(
                    success=False,
                    error="Failed to upload images",
                    platform=self.platform_name,
                )

            # Build note content with tags
            note_content = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags[:10])
                note_content = f"{content}\n\n{hashtags}"

            # Create note payload
            payload = {
                "title": title[:20],  # Max 20 chars
                "desc": note_content[:1000],  # Max 1000 chars
                "note_type": "normal",
                "image_info": {
                    "images": [
                        {"file_id": img["file_id"]} for img in uploaded_images
                    ]
                },
                "post_time": "",  # Empty for immediate posting
                "source": "web",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/sns/web/v1/feed/create",
                    headers=self._headers,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") or data.get("code") == 0:
                        note_data = data.get("data", {})
                        note_id = note_data.get("note_id", "")

                        return PublishResult(
                            success=True,
                            post_id=note_id,
                            post_url=f"{self.WEB_URL}/explore/{note_id}" if note_id else None,
                            platform=self.platform_name,
                            published_at=datetime.utcnow(),
                            raw_response=data,
                        )
                    else:
                        error_msg = data.get("msg", "Unknown error")
                        return PublishResult(
                            success=False,
                            error=error_msg,
                            platform=self.platform_name,
                        )
                else:
                    return PublishResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
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
        Fetch trending notes from Xiaohongshu.

        Args:
            query: Search keyword (if None, fetches explore/discover feed)
            limit: Maximum number of results

        Returns:
            FetchResult with list of notes
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

        # Check cookie validity
        try:
            await self.ensure_valid_cookie()
        except CookieExpiredError as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                if query:
                    # Search for notes
                    response = await client.post(
                        f"{self.BASE_URL}/api/sns/web/v1/search/notes",
                        headers=self._headers,
                        json={
                            "keyword": query,
                            "page": 1,
                            "page_size": min(limit, 40),
                            "search_id": "",
                            "sort": "general",  # or "popularity_descending"
                            "note_type": 0,
                        },
                        timeout=15.0,
                    )
                else:
                    # Fetch explore/discover feed
                    response = await client.post(
                        f"{self.BASE_URL}/api/sns/web/v1/homefeed",
                        headers=self._headers,
                        json={
                            "cursor_score": "",
                            "num": min(limit, 40),
                            "refresh_type": 1,
                            "note_index": 0,
                        },
                        timeout=15.0,
                    )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") or data.get("code") == 0:
                        notes = data.get("data", {}).get("items", [])
                        if not notes:
                            notes = data.get("data", {}).get("notes", [])

                        results = []
                        for item in notes[:limit]:
                            note = item.get("note_card", item)
                            user = note.get("user", {})
                            interact_info = note.get("interact_info", {})

                            # Extract images
                            images = []
                            image_list = note.get("image_list", note.get("images_list", []))
                            for img in image_list[:9]:
                                img_url = img.get("url_default", img.get("url", ""))
                                if img_url:
                                    images.append(img_url)

                            results.append({
                                "platform": self.platform_name,
                                "post_id": note.get("note_id", note.get("id", "")),
                                "author": user.get("nickname", user.get("nick_name", "")),
                                "author_id": user.get("user_id", user.get("userid", "")),
                                "title": note.get("title", note.get("display_title", "")),
                                "body": note.get("desc", ""),
                                "likes": interact_info.get("liked_count", note.get("liked_count", 0)),
                                "comments": interact_info.get("comment_count", note.get("comment_count", 0)),
                                "shares": interact_info.get("share_count", note.get("share_count", 0)),
                                "views": note.get("view_count", 0),
                                "published_at": note.get("time"),
                                "url": f"{self.WEB_URL}/explore/{note.get('note_id', note.get('id', ''))}",
                                "images": images,
                                "image_count": len(images),
                                "has_media": len(images) > 0,
                                "type": note.get("type", "normal"),
                            })

                        return FetchResult(
                            success=True,
                            data=results,
                            platform=self.platform_name,
                            fetched_at=datetime.utcnow(),
                            cursor=data.get("data", {}).get("cursor"),
                        )
                    else:
                        error_msg = data.get("msg", "Unknown error")
                        return FetchResult(
                            success=False,
                            error=error_msg,
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
        Fetch notes from a user.

        Args:
            user_id: User ID (defaults to authenticated user)
            limit: Maximum number of results

        Returns:
            FetchResult with list of notes
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

        # Check cookie validity
        try:
            await self.ensure_valid_cookie()
        except CookieExpiredError as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

        target_user = user_id or self._user_id
        if not target_user:
            return FetchResult(
                success=False,
                error="User ID required",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/sns/web/v1/user_posted",
                    headers=self._headers,
                    json={
                        "user_id": target_user,
                        "cursor": "",
                        "num": min(limit, 40),
                    },
                    timeout=15.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") or data.get("code") == 0:
                        notes = data.get("data", {}).get("notes", [])

                        results = []
                        for note in notes[:limit]:
                            interact_info = note.get("interact_info", {})

                            # Extract images
                            images = []
                            for img in note.get("image_list", []):
                                img_url = img.get("url_default", img.get("url", ""))
                                if img_url:
                                    images.append(img_url)

                            results.append({
                                "platform": self.platform_name,
                                "post_id": note.get("note_id", ""),
                                "author": note.get("user", {}).get("nickname", ""),
                                "author_id": target_user,
                                "title": note.get("display_title", ""),
                                "body": note.get("desc", ""),
                                "likes": interact_info.get("liked_count", 0),
                                "comments": interact_info.get("comment_count", 0),
                                "shares": interact_info.get("share_count", 0),
                                "published_at": note.get("time"),
                                "images": images,
                                "image_count": len(images),
                                "has_media": len(images) > 0,
                            })

                        return FetchResult(
                            success=True,
                            data=results,
                            platform=self.platform_name,
                            fetched_at=datetime.utcnow(),
                            cursor=data.get("data", {}).get("cursor"),
                        )
                    else:
                        return FetchResult(
                            success=False,
                            error=data.get("msg", "Unknown error"),
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

    async def fetch_note_detail(self, note_id: str) -> FetchResult:
        """
        Fetch detailed information about a specific note.

        Args:
            note_id: The note ID

        Returns:
            FetchResult with note details
        """
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/sns/web/v1/feed",
                    headers=self._headers,
                    json={
                        "source_note_id": note_id,
                    },
                    timeout=15.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") or data.get("code") == 0:
                        note_items = data.get("data", {}).get("items", [])
                        if note_items:
                            note = note_items[0].get("note_card", {})
                            user = note.get("user", {})
                            interact_info = note.get("interact_info", {})

                            # Extract images
                            images = []
                            for img in note.get("image_list", []):
                                img_url = img.get("url_default", img.get("url", ""))
                                if img_url:
                                    images.append(img_url)

                            return FetchResult(
                                success=True,
                                data=[{
                                    "platform": self.platform_name,
                                    "post_id": note.get("note_id", note_id),
                                    "author": user.get("nickname", ""),
                                    "author_id": user.get("user_id", ""),
                                    "title": note.get("title", ""),
                                    "body": note.get("desc", ""),
                                    "likes": interact_info.get("liked_count", 0),
                                    "comments": interact_info.get("comment_count", 0),
                                    "shares": interact_info.get("share_count", 0),
                                    "views": note.get("view_count", 0),
                                    "published_at": note.get("time"),
                                    "url": f"{self.WEB_URL}/explore/{note_id}",
                                    "images": images,
                                    "image_count": len(images),
                                    "has_media": len(images) > 0,
                                    "tags": note.get("tag_list", []),
                                }],
                                platform=self.platform_name,
                                fetched_at=datetime.utcnow(),
                            )

                        return FetchResult(
                            success=False,
                            error="Note not found",
                            platform=self.platform_name,
                        )
                    else:
                        return FetchResult(
                            success=False,
                            error=data.get("msg", "Unknown error"),
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
