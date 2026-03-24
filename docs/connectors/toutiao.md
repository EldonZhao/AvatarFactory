# Toutiao (今日头条) Connector

Toutiao (Jinri Toutiao / 今日头条) is China's leading news and content platform, known for its recommendation algorithm.

## Platform Overview

- **Type**: News aggregation / Content platform
- **Content Types**: Articles (图文), Microblogs (微头条), Videos
- **Character Limit**: 30 chars for title, 2,000 chars for microblog
- **Image Support**: Up to 9 images per microblog
- **API Type**: REST (OAuth 2.0)
- **Authentication**: OAuth 2.0 access token

## Prerequisites

1. Toutiao account
2. Toutiao Open Platform developer account
3. Approved app with OAuth 2.0 access
4. Access token from OAuth flow

## Getting API Credentials

### Step 1: Register as Developer

1. Go to [Toutiao Open Platform](https://open.mp.toutiao.com/)
2. Register a developer account
3. Complete verification

### Step 2: Create an App

1. Create a new application
2. Fill in app details and description
3. Submit for review (审核)
4. Wait for approval

### Step 3: Get Access Token

After approval, use OAuth 2.0 flow:

```bash
# Step 1: Authorization URL (redirect user)
https://open.snssdk.com/oauth/authorize?
  client_key=YOUR_CLIENT_KEY&
  redirect_uri=YOUR_REDIRECT_URI&
  response_type=code&
  scope=user_info,toutiao.content

# Step 2: Exchange code for token
curl -X POST "https://open.snssdk.com/oauth/access_token" \
  -d "client_key=YOUR_CLIENT_KEY" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE"
```

The response includes:
- `access_token`: Use for API calls
- `refresh_token`: For token refresh
- `expires_in`: Token expiration time

## Configuration

### Environment Variables

```bash
export TOUTIAO_ACCESS_TOKEN="your-access-token"
export TOUTIAO_CLIENT_KEY="your-client-key"        # Optional for refresh
export TOUTIAO_CLIENT_SECRET="your-client-secret"  # Optional for refresh
```

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/toutiao" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-access-token",
      "client_key": "your-client-key",
      "client_secret": "your-client-secret"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    access_token="your-access-token",
    extra={
        "client_key": "your-client-key",
        "client_secret": "your-client-secret",
    }
)
connector = get_connector("toutiao", config)
```

## Usage Examples

### Publish an Article (图文)

```python
async with connector:
    result = await connector.publish(
        content="<p>这是文章正文内容，支持HTML格式。</p>",
        title="我的文章标题",
        images=["./cover.jpg"],  # First image as cover
        tags=["科技", "人工智能"],
        article_type="article",
    )
    print(f"Article URL: {result.post_url}")
```

### Publish a Microblog (微头条)

```python
result = await connector.publish(
    content="今天分享一个好消息！🎉",
    images=["./photo1.jpg", "./photo2.jpg"],
    tags=["日常"],
    article_type="micro",  # Explicitly set as microblog
)
```

### Fetch Trending Content

```python
result = await connector.fetch_trending(limit=20)
for item in result.data:
    print(f"Title: {item['title']}")
    print(f"Views: {item['views']}, Likes: {item['likes']}")
```

### Get Article Statistics

```python
stats = await connector.get_article_stats("article_id")
print(f"Reads: {stats.get('read_count')}")
print(f"Likes: {stats.get('like_count')}")
```

## Content Types

### 1. Article (图文文章)

Long-form content with HTML support:
- **Title required**: Max 30 characters
- **Cover image**: Recommended for better visibility
- **HTML content**: Rich formatting supported
- **Tags**: Up to 5 tags

### 2. Microblog (微头条)

Short-form social content:
- **No title required**
- **Plain text**: Max 2,000 characters
- **Images**: Up to 9 images
- **Hashtags**: Use `#tag#` format

## API Response Fields

- `item_id`: Content ID
- `share_url`: Public URL to the content
- `status`: Publishing status (reviewing, published, rejected)
- `read_count`: View count
- `like_count`: Like/digg count
- `comment_count`: Comment count
- `share_count`: Share/forward count

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/toutiao/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Token expired"
- Access tokens expire; use refresh token to get new one
- Re-authorize if refresh token also expired

### "Content under review"
- Toutiao reviews all content before publishing
- Check content status in creator dashboard

### "Content rejected"
- Review Toutiao's content guidelines
- Avoid sensitive topics and promotional language

### "Permission denied"
- Ensure app has required API permissions
- Some features require higher app approval levels

## Links

- [Toutiao Open Platform](https://open.mp.toutiao.com/)
- [API Documentation](https://open.mp.toutiao.com/docs/)
- [Creator Center](https://mp.toutiao.com/)
