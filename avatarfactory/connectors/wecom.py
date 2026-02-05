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
        """Build markdown formatted message for WeChat Work."""
        parts = []

        if title:
            parts.append(f"### {title}")
            parts.append("")

        parts.append(content)

        if tags:
            parts.append("")
            parts.append(" ".join(f"`#{tag}`" for tag in tags))

        return "\n".join(parts)

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
        # Build notification content
        parts = []

        # Header
        if persona_name:
            parts.append(f"**人设**: {persona_name}")
        if platform:
            parts.append(f"**目标平台**: {platform}")
        if content_id:
            parts.append(f"**内容ID**: `{content_id}`")

        parts.append("")
        parts.append("---")
        parts.append("")

        # Content preview
        parts.append("**内容预览**:")
        parts.append("")
        # Truncate body for notification
        body_preview = content_body[:500]
        if len(content_body) > 500:
            body_preview += "..."
        parts.append(f"> {body_preview}")

        # Review results
        if review_score is not None:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("**评估结果**:")

            # Score with emoji indicator
            if review_score >= 80:
                score_indicator = "✅"
            elif review_score >= 60:
                score_indicator = "⚠️"
            else:
                score_indicator = "❌"

            parts.append(f"- 综合评分: {score_indicator} **{review_score:.0f}**/100")

            if review_summary:
                parts.append(f"- 评估摘要: {review_summary}")

        message = "\n".join(parts)

        return await self.publish(
            content=message,
            title=f"📝 新内容创作完成: {content_title}",
            tags=tags,
            message_type="markdown",
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
