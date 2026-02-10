# Weibo Connector

Weibo (微博) is China's leading microblogging platform, similar to Twitter but with unique features for the Chinese market.

## Platform Overview

- **Type**: Microblogging (Chinese market)
- **Character Limit**: 2,000 characters per post
- **Image Support**: Up to 9 images per post
- **API Type**: REST (OAuth 2.0)
- **Authentication**: OAuth 2.0

## Prerequisites

1. Weibo account
2. Weibo Open Platform developer account
3. Approved Weibo App
4. OAuth 2.0 access token

## Getting API Credentials

### Step 1: Create Developer Account

1. Go to [Weibo Open Platform](https://open.weibo.com/)
2. Register a developer account (requires Chinese mobile verification)
3. Complete real-name verification (实名认证)

### Step 2: Create an App

1. Go to **我的应用 (My Apps)** → **创建应用 (Create App)**
2. Choose app type (Web, Mobile, etc.)
3. Fill in app details:
   - 应用名称 (App Name)
   - 应用介绍 (Description)
   - 应用地址 (Website URL)
4. Wait for approval (审核中)

### Step 3: Get App Key

After approval:
- **App Key** (client_id)
- **App Secret** (client_secret)

### Step 4: Get Access Token

```bash
# Step 1: Authorization URL (redirect user)
https://api.weibo.com/oauth2/authorize?
  client_id=YOUR_APP_KEY&
  redirect_uri=YOUR_REDIRECT_URI&
  response_type=code

# Step 2: Exchange code for token
curl -X POST "https://api.weibo.com/oauth2/access_token" \
  -d "client_id=YOUR_APP_KEY" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=YOUR_REDIRECT_URI"
```

The response includes:
- `access_token`: Use this for API calls
- `uid`: User ID

## Configuration

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/weibo" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-weibo-access-token",
      "uid": "your-weibo-uid"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    access_token="your-weibo-access-token",
    extra={
        "uid": "your-weibo-uid",
    }
)
connector = get_connector("weibo", config)
```

## Usage Examples

### Publish a Post (微博)

```python
async with connector:
    result = await connector.publish(
        content="Hello Weibo! 分享一个好消息 🎉",
        tags=["科技", "人工智能"],  # Uses #tag# format
    )
    print(f"Post URL: {result.post_url}")
```

### Publish with Images

```python
result = await connector.publish(
    content="今天的美食分享 🍜",
    images=["./food1.jpg", "./food2.jpg"],  # Local file paths
    tags=["美食", "北京"],
)
```

### Fetch Trending Content

```python
result = await connector.fetch_trending(limit=20)
for post in result.data:
    print(f"@{post['author']}: {post['body'][:50]}")
```

### Search Topics

```python
result = await connector.fetch_trending(query="人工智能", limit=10)
```

## Weibo-Specific Features

### Hashtag Format

Weibo uses `#tag#` format (unlike Twitter's `#tag`):

```python
# AvatarFactory automatically converts
tags=["AI", "科技"]  # Becomes: #AI# #科技#
```

### Engagement Metrics

- `attitudes_count`: Likes (点赞)
- `comments_count`: Comments (评论)
- `reposts_count`: Reposts (转发)

## API Response Fields

- `post_id`: Weibo status ID
- `mid`: Weibo message ID (for URL)
- `body`: Post text
- `likes`: Attitude count
- `comments`: Comment count
- `shares`: Repost count

## Limitations

- **Token expiration**: Access tokens expire in 30 days
- **Rate limits**: Varies by app approval level
- **Content restrictions**: Subject to Chinese content regulations
- **App approval**: May take several days

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/weibo/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Token expired"
- Access tokens expire after 30 days
- Implement token refresh in your application

### "Permission denied"
- Some APIs require higher app approval levels
- Apply for additional permissions on open platform

### "Content blocked"
- Weibo has strict content moderation
- Avoid sensitive topics and keywords

## Links

- [Weibo Open Platform](https://open.weibo.com/)
- [API Documentation](https://open.weibo.com/wiki/)
- [OAuth 2.0 Guide](https://open.weibo.com/wiki/Oauth2/authorize)
