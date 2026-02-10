# WeCom (企业微信) Connector

WeCom (WeChat Work) connector for sending notifications via webhooks. This is a notification-only connector, not for content publishing.

## Platform Overview

- **Type**: Enterprise messaging/notifications
- **Purpose**: Send notifications to team channels
- **API Type**: Webhook
- **Authentication**: Webhook URL with key

## Use Cases

- Notify team when content is generated
- Alert on scheduled task completion
- Send review reports to team channel
- Notify on discovery/trending updates

## Prerequisites

1. WeCom workspace
2. Group chat with a webhook bot
3. Webhook URL

## Getting Webhook URL

### Step 1: Create a Group Chat

1. Open WeCom app
2. Create or select a group chat
3. Go to group settings

### Step 2: Add Webhook Bot

1. In group settings, find **Add robot**
2. Select **Custom Webhook**
3. Give it a name (e.g., "AvatarFactory")
4. Copy the webhook URL

The URL format:
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

## Configuration

### Environment Variable (System-Level)

```bash
export AVATARFACTORY_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
export AVATARFACTORY_WEBHOOK_FORMAT="wecom"
```

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/wecom" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    extra={
        "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY",
    }
)
connector = get_connector("wecom", config)
```

## Usage Examples

### Send Text Message

```python
async with connector:
    result = await connector.publish(
        content="New content generated for persona: Tech Expert",
    )
```

### Send Markdown Message

```python
result = await connector.publish(
    content="""
## Content Generation Complete

**Persona**: Tech Expert
**Topic**: AI Tools Review
**Score**: 85/100

[View Content](http://localhost:8000/content/xxx/view)
    """,
    message_type="markdown",
)
```

### Send News Card

```python
result = await connector.publish(
    content="Click to view the generated content",
    title="New Content Ready for Review",
    images=["https://example.com/cover.jpg"],
    message_type="news",
    extra={
        "url": "http://localhost:8000/content/xxx/view",
    }
)
```

## Message Types

### Text

Simple text message:
```python
await connector.publish(content="Hello!", message_type="text")
```

### Markdown

Rich formatted message:
```python
await connector.publish(
    content="**Bold** and *italic* text",
    message_type="markdown",
)
```

### News Card

Clickable card with image:
```python
await connector.publish(
    title="Card Title",
    content="Card description",
    message_type="news",
    extra={
        "url": "https://link.to/article",
        "picurl": "https://image.url/cover.jpg",
    }
)
```

## Integration with Scheduler

Enable notifications for scheduled tasks:

```python
# In persona notification config
notification = NotificationConfig(
    enabled=True,
    connector_type="wecom",
    notify_on_content=True,
    notify_on_review=True,
    notify_on_discovery=True,
)
```

## Message Format Options

Set format via environment or config:

- `wecom` - WeCom/WeChat Work (default)
- `slack` - Slack webhooks
- `discord` - Discord webhooks
- `feishu` - Feishu/Lark
- `generic` - Generic JSON webhook

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/wecom/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Webhook URL invalid"
- Check the URL format is correct
- Ensure the key parameter is included

### "Message not received"
- Verify the bot is in the group
- Check group settings allow bot messages

### "Rate limited"
- WeCom has limits on messages per minute
- Reduce notification frequency

## Links

- [WeCom Open Platform](https://open.work.weixin.qq.com/)
- [Webhook Bot Documentation](https://developer.work.weixin.qq.com/document/path/91770)
