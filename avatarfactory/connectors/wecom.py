"""
WeChat Work (企业微信) platform connector.

Supports sending messages via WeChat Work webhook (机器人).
Documentation: https://developer.work.weixin.qq.com/document/path/91770

This connector is primarily used for notifications (sending content to users)
rather than content publishing to social platforms.
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


@ConnectorRegistry.register_decorator("wecom")
@ConnectorRegistry.register_decorator("wechat_work")
@ConnectorRegistry.register_decorator("企业微信")
class WeComConnector(BasePlatformConnector):
    """
    WeChat Work (企业微信) connector.

    Uses webhook (机器人) for sending notifications.
    Supports text, markdown, and card message types.

    Configuration:
        webhook_url: The webhook URL from WeChat Work bot settings
        OR
        webhook_key: The key part of the webhook URL (after ?key=)
    """

    WEBHOOK_BASE = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._webhook_url: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "wecom"

    def _get_webhook_url(self) -> str:
        """Get the full webhook URL."""
        # Check for full URL in extra config
        webhook_url = self.config.extra.get("webhook_url")
        if webhook_url:
            return webhook_url

        # Check for webhook key
        webhook_key = self.config.extra.get("webhook_key") or self.config.api_key
        if webhook_key:
            return f"{self.WEBHOOK_BASE}?key={webhook_key}"

        raise ValueError(
            "WeChat Work webhook configuration required. "
            "Provide webhook_url or webhook_key in config.extra, or api_key"
        )

    async def connect(self) -> bool:
        """
        Initialize connection (validate webhook URL).

        WeChat Work webhooks don't require authentication beyond the URL,
        so we just validate the URL is available.
        """
        self.status = ConnectionStatus.CONNECTING

        try:
            self._webhook_url = self._get_webhook_url()
            self.status = ConnectionStatus.CONNECTED
            return True
        except ValueError as e:
            self.status = ConnectionStatus.ERROR
            raise e

    async def disconnect(self) -> None:
        """Disconnect (no-op for webhook-based connector)."""
        self._webhook_url = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """
        Verify webhook is valid by checking URL format.

        Note: WeChat Work doesn't provide a verification endpoint,
        so we just check URL format.
        """
        try:
            url = self._get_webhook_url()
            return "qyapi.weixin.qq.com" in url and "key=" in url
        except Exception:
            return False

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        message_type: str = "markdown",
        mentioned_list: Optional[List[str]] = None,
        mentioned_mobile_list: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Send message to WeChat Work group via webhook.

        Args:
            content: Message content
            title: Optional title (will be prepended as header for markdown)
            images: Not supported for webhook messages
            tags: Optional tags to append
            message_type: "text", "markdown", or "news" (default: markdown)
            mentioned_list: List of user IDs to mention (use "@all" for everyone)
            mentioned_mobile_list: List of phone numbers to mention

        Returns:
            PublishResult with success status
        """
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to WeChat Work",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build message content
            if message_type == "markdown":
                msg_content = self._build_markdown_message(
                    content, title, tags
                )
                payload = {
                    "msgtype": "markdown",
                    "markdown": {"content": msg_content},
                }
            elif message_type == "text":
                msg_content = content
                if title:
                    msg_content = f"{title}\n\n{content}"
                if tags:
                    msg_content += f"\n\n{'  '.join(f'#{tag}' for tag in tags)}"

                text_payload: Dict[str, Any] = {"content": msg_content}
                if mentioned_list:
                    text_payload["mentioned_list"] = mentioned_list
                if mentioned_mobile_list:
                    text_payload["mentioned_mobile_list"] = mentioned_mobile_list

                payload = {
                    "msgtype": "text",
                    "text": text_payload,
                }
            elif message_type == "news":
                # News card format
                payload = {
                    "msgtype": "news",
                    "news": {
                        "articles": [
                            {
                                "title": title or "新内容通知",
                                "description": content[:512],  # Max 512 chars
                                "url": kwargs.get("url", ""),
                                "picurl": images[0] if images else "",
                            }
                        ]
                    },
                }
            else:
                return PublishResult(
                    success=False,
                    error=f"Unsupported message type: {message_type}",
                    platform=self.platform_name,
                )

            # Send message
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        return PublishResult(
                            success=True,
                            post_id=str(datetime.now().timestamp()),
                            platform=self.platform_name,
                            published_at=datetime.now(),
                            raw_response=data,
                        )
                    else:
                        return PublishResult(
                            success=False,
                            error=data.get("errmsg", "Unknown error"),
                            platform=self.platform_name,
                            raw_response=data,
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

    def _build_markdown_message(
        self,
        content: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Build markdown formatted message for WeChat Work.

        Note: WeChat Work only supports limited markdown:
        - Headers: # ## ###
        - Bold: **text**
        - Links: [text](url)
        - Inline code: `code`
        - Quote: > text
        - Green text: <font color="info">text</font>
        - Grey text: <font color="comment">text</font>
        - Orange text: <font color="warning">text</font>

        NOT supported:
        - Italics, strikethrough
        - Lists (-, *, 1.)
        - Tables
        - Code blocks (```)
        - Images

        Max length: 4096 bytes
        """
        parts = []

        if title:
            parts.append(f"### {title}")
            parts.append("")

        # Convert unsupported markdown to plain text
        cleaned_content = self._clean_markdown_for_wecom(content)
        parts.append(cleaned_content)

        if tags:
            parts.append("")
            parts.append(" ".join(f"`#{tag}`" for tag in tags[:5]))  # Limit tags

        result = "\n".join(parts)

        # Truncate to max 4096 bytes (with buffer for Chinese chars)
        max_chars = 1200  # ~3600 bytes for Chinese
        if len(result) > max_chars:
            result = result[:max_chars] + "\n\n...(内容已截断)"

        return result

    def _clean_markdown_for_wecom(self, content: str) -> str:
        """
        Clean markdown content to be compatible with WeChat Work.

        Converts unsupported markdown syntax to plain text or supported alternatives.
        """
        import re

        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            # Convert list items to plain text with indicators
            # - item -> • item
            line = re.sub(r"^(\s*)[-*]\s+", r"\1• ", line)

            # Convert numbered lists
            # 1. item -> 1. item (keep as is, just ensure spacing)
            line = re.sub(r"^(\s*)(\d+)\.\s+", r"\1\2. ", line)

            # Remove code blocks markers (``` or ```python)
            if line.strip().startswith("```"):
                continue

            # Convert **bold** to keep it (supported)
            # But remove *italic* or _italic_ (not supported)
            line = re.sub(r"(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)", r"\1", line)
            line = re.sub(r"_([^_]+)_", r"\1", line)

            # Remove strikethrough ~~text~~
            line = re.sub(r"~~([^~]+)~~", r"\1", line)

            # Keep headers, bold, quotes, inline code (all supported)

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    async def send_content_notification(
        self,
        content_title: str,
        content_body: str,
        review_score: Optional[float] = None,
        review_summary: Optional[str] = None,
        content_id: Optional[str] = None,
        persona_name: Optional[str] = None,
        platform: Optional[str] = None,
        tags: Optional[List[str]] = None,
        content_url: Optional[str] = None,
    ) -> PublishResult:
        """
        Send content creation notification using news card format.

        This method uses WeChat Work's news card format which supports:
        - Clean card-style display
        - Clickable link to view full content
        - Short description preview

        Args:
            content_title: Generated content title
            content_body: Generated content body (used for description)
            review_score: Optional review score (0-100)
            review_summary: Optional review summary text
            content_id: Content ID for building view URL
            persona_name: Optional persona name
            platform: Target platform name
            tags: Content tags
            content_url: Optional custom URL (if not provided, uses service URL)

        Returns:
            PublishResult
        """
        import os

        # Build description (max 512 chars for WeChat Work news card)
        description_parts = []

        # Add persona and platform info
        if persona_name:
            description_parts.append(f"👤 {persona_name}")
        if platform:
            description_parts.append(f"📱 {platform}")

        # Add review score
        if review_score is not None:
            if review_score >= 80:
                description_parts.append(f"✅ 评分: {review_score:.0f}/100")
            elif review_score >= 60:
                description_parts.append(f"⚠️ 评分: {review_score:.0f}/100")
            else:
                description_parts.append(f"❌ 评分: {review_score:.0f}/100")

        # Add content preview
        body_clean = self._strip_markdown(content_body)
        # Calculate remaining space for preview
        header_len = len(" | ".join(description_parts)) + 4 if description_parts else 0
        max_preview_len = min(400, 500 - header_len)
        body_preview = body_clean[:max_preview_len]
        if len(body_clean) > max_preview_len:
            body_preview += "..."

        if description_parts:
            description = " | ".join(description_parts) + "\n\n" + body_preview
        else:
            description = body_preview

        # Build title
        title = f"📝 {content_title}"
        if len(title) > 60:
            title = title[:57] + "..."

        # Build URL
        url = content_url
        if not url and content_id:
            # Try to get service URL from env
            service_url = os.getenv("AVATARFACTORY_SERVICE_URL", "").rstrip("/")
            if service_url:
                url = f"{service_url}/content/{content_id}/view"

        # If no URL available, fall back to text message type
        if not url:
            # WeChat Work news card requires a URL, fall back to text
            return await self.publish(
                content=description,
                title=title,
                message_type="text",
            )

        # Use news card format
        return await self.publish(
            content=description,
            title=title,
            message_type="news",
            url=url,
        )

    def _strip_markdown(self, text: str) -> str:
        """Strip markdown formatting for plain text preview."""
        import re

        # Remove headers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
        text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
        # Remove inline code
        text = re.sub(r"`([^`]+)`", r"\1", text)
        # Remove links, keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        # Remove blockquotes
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        # Remove horizontal rules
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
        # Collapse multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    async def send_message(
        self,
        message: str,
        message_type: str = "markdown",
    ) -> PublishResult:
        """
        Send a simple text/markdown message.

        This is a convenience method for sending simple notifications.

        Args:
            message: Message content
            message_type: "text" or "markdown" (default: markdown)

        Returns:
            PublishResult
        """
        return await self.publish(
            content=message,
            message_type=message_type,
        )

    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch trending content (not supported for WeChat Work webhook).

        WeChat Work webhooks are for sending messages only.
        """
        return FetchResult(
            success=False,
            error="WeChat Work webhook does not support fetching content",
            platform=self.platform_name,
        )

    async def fetch_user_posts(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch user posts (not supported for WeChat Work webhook).

        WeChat Work webhooks are for sending messages only.
        """
        return FetchResult(
            success=False,
            error="WeChat Work webhook does not support fetching posts",
            platform=self.platform_name,
        )
