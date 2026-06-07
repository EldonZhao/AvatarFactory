"""
Webhook notification provider.

Supports various webhook formats including:
- Generic JSON webhook
- Slack incoming webhook
- Discord webhook
- Feishu/Lark webhook
- WeCom/WeChat Work webhook
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from avatarfactory.notifications.base import (
    NotificationMessage,
    NotificationProvider,
    NotificationResult,
)

logger = logging.getLogger("avatarfactory.notifications.webhook")


class WebhookNotifier(NotificationProvider):
    """
    Webhook notification provider.

    Sends notifications via HTTP POST to a webhook URL.
    Supports multiple formats for different services.
    """

    FORMATS = ["generic", "slack", "discord", "feishu", "wecom"]

    def __init__(
        self,
        webhook_url: str,
        format: str = "generic",
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(f"webhook_{format}")
        self.webhook_url = webhook_url
        self.format = format
        self.headers = headers or {}

    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Send notification via webhook."""
        try:
            import httpx
        except ImportError:
            return NotificationResult(
                success=False,
                provider=self.name,
                error="httpx required for webhook notifications",
            )

        try:
            payload = self._format_payload(message)
            headers = {
                "Content-Type": "application/json",
                **self.headers,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code in (200, 201, 204):
                    return NotificationResult(
                        success=True,
                        provider=self.name,
                        message_id=f"webhook_{datetime.now().timestamp()}",
                    )
                else:
                    return NotificationResult(
                        success=False,
                        provider=self.name,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                    )

        except Exception as e:
            return NotificationResult(
                success=False,
                provider=self.name,
                error=str(e),
            )

    def _format_payload(self, message: NotificationMessage) -> Dict[str, Any]:
        """Format payload based on webhook type."""
        if self.format == "slack":
            return self._format_slack(message)
        elif self.format == "discord":
            return self._format_discord(message)
        elif self.format == "feishu":
            return self._format_feishu(message)
        elif self.format == "wecom":
            return self._format_wecom(message)
        else:
            return self._format_generic(message)

    def _format_generic(self, message: NotificationMessage) -> Dict[str, Any]:
        """Generic JSON format."""
        return {
            "title": message.title,
            "body": message.body,
            "priority": message.priority.value,
            "category": message.category,
            "action_url": message.action_url,
            "timestamp": message.created_at.isoformat(),
            "metadata": message.metadata,
        }

    def _format_slack(self, message: NotificationMessage) -> Dict[str, Any]:
        """Slack incoming webhook format."""
        # Priority to color
        color = {
            "low": "#808080",
            "normal": "#36a64f",
            "high": "#ffcc00",
            "urgent": "#ff0000",
        }.get(message.priority.value, "#36a64f")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": message.title,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message.body,
                }
            },
        ]

        if message.action_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View",
                        },
                        "url": message.action_url,
                    }
                ]
            })

        return {
            "attachments": [{"color": color, "blocks": blocks}]
        }

    def _format_discord(self, message: NotificationMessage) -> Dict[str, Any]:
        """Discord webhook format."""
        color = {
            "low": 0x808080,
            "normal": 0x00ff00,
            "high": 0xffcc00,
            "urgent": 0xff0000,
        }.get(message.priority.value, 0x00ff00)

        embed = {
            "title": message.title,
            "description": message.body,
            "color": color,
            "timestamp": message.created_at.isoformat(),
        }

        if message.action_url:
            embed["url"] = message.action_url

        return {"embeds": [embed]}

    def _format_feishu(self, message: NotificationMessage) -> Dict[str, Any]:
        """Feishu/Lark webhook format."""
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": message.title,
                    },
                    "template": {
                        "low": "grey",
                        "normal": "blue",
                        "high": "orange",
                        "urgent": "red",
                    }.get(message.priority.value, "blue"),
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": message.body,
                        }
                    }
                ],
            }
        }

    def _format_wecom(self, message: NotificationMessage) -> Dict[str, Any]:
        """WeCom/WeChat Work webhook format."""
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {message.title}\n{message.body}",
            }
        }

    def validate_config(self) -> bool:
        """Validate webhook configuration."""
        if not self.webhook_url:
            return False
        if self.format not in self.FORMATS:
            return False
        return True
