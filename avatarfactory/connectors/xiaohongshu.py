"""
Xiaohongshu (小红书) platform connector.

Xiaohongshu does not have an official public API. This connector uses
the xhs library for API interaction.

IMPORTANT:
- This connector is EXPERIMENTAL due to XHS's anti-bot measures
- Cookie authentication may fail due to signature requirements
- For reliable usage, consider manual posting or browser automation

Dependencies:
    pip install xhs
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


class CookieExpiredError(Exception):
    """Raised when the Xiaohongshu cookie has expired."""
    pass


class CookieExpiringWarning(Warning):
    """Warning when the cookie is about to expire."""
    pass


@ConnectorRegistry.register_decorator("xiaohongshu")
@ConnectorRegistry.register_decorator("xhs")
class XiaohongshuConnector(BasePlatformConnector):
    """
    Xiaohongshu platform connector using xhs library with Playwright signing.

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

    # Cookie expiration settings
    COOKIE_WARNING_DAYS = 3
    COOKIE_CHECK_INTERVAL = 3600

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._cookie: Optional[str] = None
        self._user_id: Optional[str] = None
        self._xhs_client: Any = None
        self._last_cookie_check: Optional[datetime] = None
        self._cookie_valid: bool = False
        self._consecutive_failures: int = 0

    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="xiaohongshu",
            display_name="Xiaohongshu (小红书)",
            description="Xiaohongshu (Little Red Book) content platform",
            supports_topic_discovery=True,
            supports_persona_discovery=True,
            supports_publishing=True,
            supports_fetching=True,
            config_fields=[
                ConnectorConfigField(
                    name="cookie",
                    label="Cookie",
                    field_type="textarea",
                    required=True,
                    description=(
                        "Browser cookie string (extract from browser"
                        " DevTools, valid for 7-30 days)"
                    ),
                    placeholder="Paste cookie string from browser",
                    env_var="XIAOHONGSHU_COOKIE",
                ),
                ConnectorConfigField(
                    name="user_id",
                    label="User ID",
                    field_type="text",
                    required=False,
                    description=(
                        "Xiaohongshu user ID for fetching own posts"
                    ),
                    env_var="XIAOHONGSHU_USER_ID",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Requires cookie-based"
                " authentication (extract from browser). Call"
                " connector.fetch_trending(query) for topic discovery of"
                " popular notes. Call connector.fetch_user_posts(user_id)"
                " for persona analysis of content creators. Publishing"
                " requires title + at least 1 image. Note: Cookie expires"
                " every 7-30 days and must be refreshed manually."
                " Experimental due to anti-bot protections."
            ),
        )

    def _get_sign_function(self):
        """Get the sign function from xhs library."""
        try:
            from xhs.help import sign as xhs_sign

            # Extract a1 and b1 from config/cookie
            a1_value = ""
            b1_value = ""

            if self._cookie:
                import re
                a1_match = re.search(r'a1=([^;]+)', self._cookie)
                a1_value = a1_match.group(1) if a1_match else ""

            # b1 can be passed in extra config
            b1_value = self.config.extra.get("b1", "")

            # Wrapper to match expected signature (accepts any kwargs)
            def sign_wrapper(uri, data=None, **kwargs):
                a1 = kwargs.get('a1', a1_value)
                b1 = kwargs.get('b1', b1_value)
                return xhs_sign(uri, data, a1=a1, b1=b1)

            return sign_wrapper
        except ImportError:
            return None

    async def connect(self) -> bool:
        """Connect to Xiaohongshu using cookie authentication with xhs library."""
        try:
            from xhs import XhsClient
        except ImportError:
            raise ImportError(
                "xhs library required for Xiaohongshu connector.\n"
                "Install with: pip install xhs"
            )

        self._cookie = self.config.extra.get("cookie") or self.config.extra.get("cookies")
        self._user_id = self.config.extra.get("user_id")

        if not self._cookie:
            raise ValueError(
                "Xiaohongshu requires cookie authentication. "
                "Set cookie in config.extra['cookie']"
            )

        self.status = ConnectionStatus.CONNECTING

        try:
            # Get sign function
            sign_func = self._get_sign_function()

            # Create XHS client
            self._xhs_client = XhsClient(
                cookie=self._cookie,
                sign=sign_func,
            )

            # Try to verify connection
            try:
                if await self.verify_credentials():
                    self.status = ConnectionStatus.CONNECTED
                    return True
            except Exception:
                pass

            # If verification fails, still mark as connected but warn
            # Some operations might still work
            self.status = ConnectionStatus.CONNECTED
            self._cookie_valid = False
            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(
                f"Failed to connect to Xiaohongshu: {e}\n\n"
                "Note: Xiaohongshu's API requires special signatures that may fail.\n"
                "If you see this error, try:\n"
                "1. Refresh your cookie from browser\n"
                "2. Wait a few minutes and try again\n"
                "3. Use manual posting via browser instead"
            )

    async def disconnect(self) -> None:
        """Disconnect from Xiaohongshu."""
        self._xhs_client = None
        self._cookie = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify that the cookie is valid."""
        if not self._xhs_client:
            return False

        try:
            # Try to get self info to verify cookie
            info = self._xhs_client.get_self_info()
            if info and info.get("user_id"):
                self._user_id = info["user_id"]
                self._cookie_valid = True
                self._consecutive_failures = 0
                self._last_cookie_check = datetime.now()
                return True
            return False
        except Exception:
            self._consecutive_failures += 1
            return False

    async def check_cookie_status(self) -> Tuple[bool, Optional[str]]:
        """Check if the cookie is still valid."""
        if self._last_cookie_check:
            elapsed = (datetime.now() - self._last_cookie_check).total_seconds()
            if elapsed < self.COOKIE_CHECK_INTERVAL and self._cookie_valid:
                return (True, None)

        try:
            is_valid = await self.verify_credentials()
            if not is_valid:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    return (False, "Cookie appears to be expired. Please refresh your cookie.")
                return (False, f"Cookie check failed ({self._consecutive_failures}/3 attempts)")
            return (True, None)
        except Exception as e:
            return (False, f"Error checking cookie: {e}")

    async def ensure_valid_cookie(self) -> None:
        """Ensure cookie is valid before making requests."""
        is_valid, message = await self.check_cookie_status()
        if not is_valid:
            self.status = ConnectionStatus.ERROR
            raise CookieExpiredError(
                message or "Cookie has expired. Please update XIAOHONGSHU_COOKIE."
            )
        if message:
            import warnings
            warnings.warn(message, CookieExpiringWarning)

    def get_cookie_refresh_instructions(self) -> str:
        """Return instructions for refreshing the cookie."""
        return """
=====================================================================
          How to Refresh Xiaohongshu Cookie
=====================================================================

  1. Open browser, visit https://www.xiaohongshu.com
  2. Login to your account
  3. Press F12 to open Developer Tools
  4. Switch to Network tab
  5. Refresh the page, click any request
  6. Find Cookie field in Headers
  7. Copy the full Cookie value
  8. Update XIAOHONGSHU_COOKIE in your .env file

  Cookie is typically valid for 7-30 days.

=====================================================================
"""

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

        Note: Xiaohongshu requires at least one image and a title.
        """
        if not self.is_connected() or not self._xhs_client:
            return PublishResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

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
            # Build note content with tags
            note_content = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags[:10])
                note_content = f"{content}\n\n{hashtags}"

            # Upload images and create note
            result = self._xhs_client.create_image_note(
                title=title[:20],
                desc=note_content[:1000],
                files=images[:9],
                is_private=False,
            )

            if result and result.get("note_id"):
                note_id = result["note_id"]
                return PublishResult(
                    success=True,
                    post_id=note_id,
                    post_url=f"https://www.xiaohongshu.com/explore/{note_id}",
                    platform=self.platform_name,
                    published_at=datetime.utcnow(),
                    raw_response=result,
                )
            else:
                return PublishResult(
                    success=False,
                    error=result.get("msg", "Unknown error"),
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
        """Fetch trending notes from Xiaohongshu."""
        if not self.is_connected() or not self._xhs_client:
            return FetchResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

        try:
            if query:
                # Search for notes
                data = self._xhs_client.get_note_by_keyword(
                    keyword=query,
                    page=1,
                    page_size=min(limit, 20),
                )
                notes = data.get("items", [])
            else:
                # Get home feed (recommend feed)
                from xhs import FeedType
                data = self._xhs_client.get_home_feed(feed_type=FeedType.RECOMMEND)
                notes = data.get("items", data.get("notes", []))

            results = []
            for note in notes[:limit]:
                note_card = note.get("note_card", note)
                user = note_card.get("user", {})
                interact_info = note_card.get("interact_info", {})

                # Extract images
                images = []
                for img in note_card.get("image_list", []):
                    img_url = img.get("url_default", img.get("url", ""))
                    if img_url:
                        images.append(img_url)

                results.append({
                    "platform": self.platform_name,
                    "post_id": note_card.get("note_id", note.get("id", "")),
                    "author": user.get("nickname", ""),
                    "author_id": user.get("user_id", ""),
                    "title": note_card.get("display_title", note_card.get("title", "")),
                    "body": note_card.get("desc", ""),
                    "likes": interact_info.get("liked_count", 0),
                    "comments": interact_info.get("comment_count", 0),
                    "shares": interact_info.get("share_count", 0),
                    "url": f"https://www.xiaohongshu.com/explore/{note_card.get('note_id', '')}",
                    "images": images,
                    "image_count": len(images),
                    "has_media": len(images) > 0,
                })

            self._cookie_valid = True
            self._last_cookie_check = datetime.now()

            return FetchResult(
                success=True,
                data=results,
                platform=self.platform_name,
                fetched_at=datetime.utcnow(),
            )

        except Exception as e:
            error_msg = str(e)

            # Check for specific error codes
            if "300011" in error_msg or "账号存在异常" in error_msg:
                return FetchResult(
                    success=False,
                    error=(
                        "账号被限制 (Error 300011)\n\n"
                        "小红书检测到异常访问，请:\n"
                        "1. 在浏览器中打开 xiaohongshu.com 并完成验证\n"
                        "2. 等待几小时后重试\n"
                        "3. 重新获取 Cookie"
                    ),
                    platform=self.platform_name,
                )

            # Check for specific error types
            if "DataFetchError" in type(e).__name__ or "code" in error_msg:
                return FetchResult(
                    success=False,
                    error=(
                        f"API request failed: {error_msg}\n\n"
                        "This is likely due to Xiaohongshu's anti-bot protection.\n"
                        "The xhs library's signature may be outdated.\n\n"
                        "Workarounds:\n"
                        "1. Try again later\n"
                        "2. Update xhs library: pip install --upgrade xhs\n"
                        "3. Use manual browser-based posting"
                    ),
                    platform=self.platform_name,
                )

            if "cookie" in error_msg.lower() or "login" in error_msg.lower():
                return FetchResult(
                    success=False,
                    error=f"Cookie expired: {error_msg}. Please refresh your cookie.",
                    platform=self.platform_name,
                )

            return FetchResult(
                success=False,
                error=error_msg,
                platform=self.platform_name,
            )

    async def fetch_user_posts(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """Fetch notes from a user."""
        if not self.is_connected() or not self._xhs_client:
            return FetchResult(
                success=False,
                error="Not connected to Xiaohongshu",
                platform=self.platform_name,
            )

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
            data = self._xhs_client.get_user_notes(user_id=target_user)
            notes = data.get("notes", [])

            results = []
            for note in notes[:limit]:
                interact_info = note.get("interact_info", {})

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
                    "images": images,
                    "image_count": len(images),
                    "has_media": len(images) > 0,
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
