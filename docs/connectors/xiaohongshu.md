# Xiaohongshu (小红书) Connector

Xiaohongshu (Little Red Book) is China's leading lifestyle and e-commerce platform, popular for beauty, fashion, and travel content.

## Platform Overview

- **Type**: Lifestyle/social commerce
- **Content**: Text + images (visual-first)
- **Character Limit**: 1,000 characters per note
- **Image Support**: Up to 18 images per note
- **API Type**: Private (cookie-based)
- **Authentication**: Cookie + xhs signature

## Important Notes

⚠️ **Xiaohongshu has no public API**. This connector uses cookie-based authentication similar to browser sessions. Use responsibly and respect rate limits.

## Prerequisites

1. Xiaohongshu account
2. Browser cookies (extracted from logged-in session)
3. User ID

## Getting Credentials

### Step 1: Log in to Xiaohongshu

1. Open [xiaohongshu.com](https://www.xiaohongshu.com/) in a browser
2. Log in with your account
3. Make sure the session is active

### Step 2: Extract Cookies

Using browser developer tools:

1. Open DevTools (F12)
2. Go to **Application** → **Cookies**
3. Find `xiaohongshu.com` cookies
4. Copy the full cookie string (all cookies)

Key cookies needed:
- `web_session`
- `a1`
- `webId`

### Step 3: Get User ID

1. Go to your profile page
2. The URL contains your user ID: `xiaohongshu.com/user/profile/YOUR_USER_ID`

### Cookie Format

```
web_session=xxx; a1=xxx; webId=xxx; ...
```

## Configuration

### Environment Variables

```bash
export XIAOHONGSHU_COOKIE="web_session=xxx; a1=xxx; webId=xxx; ..."
export XIAOHONGSHU_USER_ID="your-user-id"
```

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/xiaohongshu" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "cookie": "web_session=xxx; a1=xxx; ...",
      "user_id": "your-user-id"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    extra={
        "cookie": "web_session=xxx; a1=xxx; ...",
        "user_id": "your-user-id",
    }
)
connector = get_connector("xiaohongshu", config)
# or use alias
connector = get_connector("xhs", config)
```

## Usage Examples

### Publish a Note

```python
async with connector:
    result = await connector.publish(
        content="分享我最近发现的好物！✨\n\n真的超级推荐...",
        title="超好用的护肤品推荐",
        images=["./product1.jpg", "./product2.jpg"],
        tags=["护肤", "好物推荐", "种草"],
    )
    print(f"Note URL: {result.post_url}")
```

### Fetch Trending Notes

```python
result = await connector.fetch_trending(query="护肤", limit=20)
for note in result.data:
    print(f"@{note['author']}: {note['title']}")
    print(f"  Likes: {note['likes']}, Collects: {note['collects']}")
```

### Fetch User Notes

```python
result = await connector.fetch_user_posts(limit=10)
```

## Content Best Practices

### For Xiaohongshu:

1. **Visual-first**: High-quality images are essential
2. **Title matters**: Eye-catching titles boost engagement
3. **Emoji usage**: Moderate emoji use is expected
4. **Hashtags**: Use relevant topic tags (#话题#)
5. **Length**: Medium-length notes perform best

### Example Note Structure

```python
content = """
📍今天来分享一下我的日常护肤流程~

✨第一步：清洁
选择温和的氨基酸洗面奶，不会过度清洁

✨第二步：水乳
这款精华水真的超级好用！

💰价格：199元
📦购买渠道：官方旗舰店

#护肤 #日常分享 #好物推荐
"""
```

## API Response Fields

- `note_id`: Note ID
- `title`: Note title
- `body`: Note content
- `likes`: Like count
- `collects`: Collection/save count
- `comments`: Comment count
- `shares`: Share count
- `images`: Image URLs

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/xiaohongshu/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Session expired"
- Cookies expire periodically
- Re-extract cookies from a fresh browser session
- Consider using browser automation for fresh sessions

### "Signature verification failed"
- The xhs signature may need updating
- Check if the signing algorithm has changed

### "Content rejected"
- Xiaohongshu has strict content moderation
- Avoid promotional language or sensitive topics
- Images are scanned for violations

### "Rate limited"
- Slow down request frequency
- Wait before retrying

## Security Considerations

1. **Cookie safety**: Store cookies securely (encrypted)
2. **Session management**: Cookies may expire, plan for refresh
3. **Rate limits**: Respect platform limits
4. **TOS compliance**: Review Xiaohongshu terms of service

## Links

- [Xiaohongshu](https://www.xiaohongshu.com/)
- [Creator Center](https://creator.xiaohongshu.com/)
