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
    ) -> PublishResult:
        """
        Send content creation notification with review results.

        This is a convenience method for the common use case of
        notifying users about newly generated content.

        Note: WeChat Work has limited markdown support and 4096 byte limit.
        This method formats the notification to work within those constraints.

        Args:
            content_title: Generated content title
            content_body: Generated content body (will be truncated)
            review_score: Optional review score (0-100)
            review_summary: Optional review summary text
            content_id: Optional content ID for reference
            persona_name: Optional persona name
            platform: Target platform name
            tags: Content tags

        Returns:
            PublishResult
        """
        # Build notification content (optimized for WeChat Work)
        parts = []

        # Compact header
        header_parts = []
        if persona_name:
            header_parts.append(f"人设: {persona_name}")
        if platform:
            header_parts.append(f"平台: {platform}")
        if content_id:
            header_parts.append(f"ID: {content_id}")

        if header_parts:
            parts.append(" | ".join(header_parts))
            parts.append("")

        # Review score (prominent)
        if review_score is not None:
            if review_score >= 80:
                score_text = f"<font color=\"info\">评分: {review_score:.0f}/100 ✅</font>"
            elif review_score >= 60:
                score_text = f"<font color=\"warning\">评分: {review_score:.0f}/100 ⚠️</font>"
            else:
                score_text = f"<font color=\"warning\">评分: {review_score:.0f}/100 ❌</font>"
            parts.append(score_text)
            parts.append("")

        # Content preview - very short for notification
        # Strip markdown formatting for cleaner preview
        body_clean = self._strip_markdown(content_body)
        body_preview = body_clean[:300]
        if len(body_clean) > 300:
            body_preview += "..."

        parts.append(f"> {body_preview}")

        # Review summary (if any)
        if review_summary:
            parts.append("")
            parts.append(f"<font color=\"comment\">审核备注: {review_summary[:100]}</font>")

        message = "\n".join(parts)

        # Use text type for longer content with cleaner display
        return await self.publish(
            content=message,
            title=f"📝 {content_title[:30]}{'...' if len(content_title) > 30 else ''}",
            tags=tags[:3] if tags else None,  # Limit tags
            message_type="markdown",
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
