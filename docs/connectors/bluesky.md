# Bluesky Connector

Bluesky is a decentralized social network built on the AT Protocol. It's one of the easiest platforms to integrate with due to its open API.

## Platform Overview

- **Type**: Microblogging (Twitter-like)
- **Character Limit**: 300 characters per post
- **Image Support**: Up to 4 images per post
- **API Type**: REST (AT Protocol)
- **Authentication**: App Password

## Prerequisites

1. A Bluesky account ([bsky.app](https://bsky.app))
2. An App Password (not your main password)

## Getting App Password

1. Log in to Bluesky at [bsky.app](https://bsky.app)
2. Go to **Settings** → **Privacy and Security** → **App Passwords**
3. Click **Add App Password**
4. Give it a name (e.g., "AvatarFactory")
5. Copy the generated password immediately (it won't be shown again)

## Configuration

### Environment Variables

```bash
export BLUESKY_USERNAME="your-handle.bsky.social"
export BLUESKY_PASSWORD="your-app-password"  # NOT your main password
```

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/bluesky" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "username": "your-handle.bsky.social",
      "password": "your-app-password"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    username="your-handle.bsky.social",
    password="your-app-password",
)
connector = get_connector("bluesky", config)
```

## Usage Examples

### Publish a Post

```python
async with connector:
    result = await connector.publish(
        content="Hello Bluesky! 🦋",
        tags=["ai", "avatarfactory"],
    )
    print(f"Post URL: {result.post_url}")
```

### Publish with Images

```python
result = await connector.publish(
    content="Check out this image!",
    images=["./path/to/image.jpg"],
    alt_texts=["Description of the image"],
)
```

### Publish a Thread

```python
results = await connector.publish_thread(
    posts=[
        "This is the first post of my thread 🧵",
        "This is the second post with more details...",
        "And this is the conclusion!",
    ],
    images=["./header.jpg"],  # Attached to first post only
)
```

### Fetch Trending Content

```python
result = await connector.fetch_trending(limit=20)
for post in result.data:
    print(f"@{post['author']}: {post['body'][:100]}")
    print(f"  Likes: {post['likes']}, Comments: {post['comments']}")
```

### Search Posts

```python
result = await connector.search(query="AI tools", limit=10)
```

## API Response Fields

### Publish Result
- `post_id`: AT Protocol post ID
- `post_url`: Full URL to the post on bsky.app
- `raw_response`: Contains `uri` and `cid` for threading

### Fetch Result
- `post_id`: Post ID
- `author`: Handle (e.g., "user.bsky.social")
- `author_id`: DID (Decentralized Identifier)
- `body`: Post text
- `likes`, `comments`, `shares`: Engagement metrics
- `images`: List of image URLs
- `url`: Post permalink

## Verification

Test your connection:

```bash
# CLI
avatarfactory connectors test bluesky

# API
curl -X POST "http://localhost:8000/tenant/connectors/bluesky/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Invalid identifier or password"
- Ensure you're using an App Password, not your main password
- Check the username is in the correct format (with `.bsky.social` suffix)

### "Rate limit exceeded"
- Bluesky has rate limits on API calls
- Implement backoff and retry logic

### "Session expired"
- App passwords can expire; generate a new one if needed

## Links

- [Bluesky App](https://bsky.app)
- [AT Protocol Documentation](https://atproto.com/docs)
- [Bluesky API Reference](https://docs.bsky.app)
