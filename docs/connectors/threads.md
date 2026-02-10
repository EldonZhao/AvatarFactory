# Threads Connector

Threads is Meta's text-based social app, similar to Twitter. It uses the Threads API (based on the Graph API).

## Platform Overview

- **Type**: Microblogging
- **Character Limit**: 500 characters per post
- **Image Support**: Yes (via URL)
- **API Type**: Meta Graph API
- **Authentication**: OAuth 2.0 via Meta

## Prerequisites

1. Instagram account (Threads uses Instagram login)
2. Meta Developer App with Threads API access
3. OAuth 2.0 access token

## Getting API Credentials

### Step 1: Create a Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app, select **Business** type
3. Add **Threads API** product to your app

### Step 2: Configure OAuth

1. In App Settings, go to **Use cases** → **Threads API**
2. Add OAuth redirect URIs
3. Configure permissions:
   - `threads_basic` - Read profile
   - `threads_content_publish` - Publish content
   - `threads_read_replies` - Read replies

### Step 3: Get Access Token

```bash
# Step 1: Authorization URL
https://threads.net/oauth/authorize?
  client_id=YOUR_APP_ID&
  redirect_uri=YOUR_REDIRECT_URI&
  scope=threads_basic,threads_content_publish&
  response_type=code

# Step 2: Exchange code for short-lived token
curl -X POST "https://graph.threads.net/oauth/access_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "grant_type=authorization_code" \
  -d "redirect_uri=YOUR_REDIRECT_URI" \
  -d "code=AUTHORIZATION_CODE"

# Step 3: Exchange for long-lived token
curl "https://graph.threads.net/access_token?
  grant_type=th_exchange_token&
  client_secret=YOUR_APP_SECRET&
  access_token=SHORT_LIVED_TOKEN"
```

### Step 4: Get User ID

```bash
curl "https://graph.threads.net/v1.0/me?
  fields=id,username&
  access_token=YOUR_ACCESS_TOKEN"
```

## Configuration

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/threads" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-threads-access-token",
      "user_id": "your-threads-user-id"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    access_token="your-threads-access-token",
    extra={
        "user_id": "your-threads-user-id",
    }
)
connector = get_connector("threads", config)
```

## Usage Examples

### Publish a Text Post

```python
async with connector:
    result = await connector.publish(
        content="Hello Threads! 👋",
        tags=["ai", "tech"],
    )
    print(f"Post URL: {result.post_url}")
```

### Publish with Image

```python
result = await connector.publish(
    content="Check out this image!",
    images=["https://example.com/image.jpg"],  # Must be public URL
)
```

### Reply to a Post

```python
result = await connector.publish(
    content="Great point! Here's my thoughts...",
    reply_to="original_post_id",
)
```

### Fetch Your Posts

```python
result = await connector.fetch_user_posts(limit=20)
for post in result.data:
    print(f"{post['body'][:50]}... - {post['likes']} likes")
```

## Publishing Flow

Threads uses a two-step publishing process:

1. **Create container**: Prepare the post content
2. **Publish container**: Actually publish the post

The connector handles this automatically.

## API Response Fields

- `post_id`: Threads post ID
- `body`: Post text
- `likes`: Like count (reply_count)
- `comments`: Reply count
- `url`: Post permalink
- `media_type`: TEXT, IMAGE, etc.

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/threads/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Invalid access token"
- Tokens expire; get a long-lived token
- Ensure correct permissions are granted

### "Container creation failed"
- Check image URLs are publicly accessible
- Verify text length is within limit

### "User ID not found"
- User ID must be obtained from the OAuth flow
- Use `/me` endpoint to get your user ID

## Links

- [Threads API Documentation](https://developers.facebook.com/docs/threads)
- [Meta for Developers](https://developers.facebook.com/)
- [Graph API Reference](https://developers.facebook.com/docs/graph-api)
