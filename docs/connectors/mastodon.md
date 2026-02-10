# Mastodon Connector

Mastodon is a decentralized, open-source social network. The connector works with any Mastodon instance.

## Platform Overview

- **Type**: Decentralized microblogging
- **Character Limit**: 500 characters (default, varies by instance)
- **Image Support**: Up to 4 images per post
- **API Type**: REST
- **Authentication**: OAuth 2.0

## Key Advantages

- **Open source**: Fully transparent codebase
- **Decentralized**: Choose your instance or self-host
- **Simple API**: Easy to integrate
- **No algorithm**: Chronological timeline

## Prerequisites

1. Mastodon account on any instance
2. Application registration on your instance
3. OAuth 2.0 access token

## Getting API Credentials

### Step 1: Register an Application

Go to your Mastodon instance settings:

```
https://your-instance.social/settings/applications/new
```

Fill in:
- **Application name**: e.g., "AvatarFactory"
- **Redirect URI**: Your callback URL or `urn:ietf:wg:oauth:2.0:oob` for local
- **Scopes**: Select `read`, `write`, `push` as needed

### Step 2: Get Access Token

After creating the app, you'll get:
- **Client key** (client_id)
- **Client secret** (client_secret)

For personal use, you can also get an access token directly from the app settings page.

For OAuth flow:

```bash
# Step 1: Authorization URL
https://your-instance.social/oauth/authorize?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=YOUR_REDIRECT_URI&
  response_type=code&
  scope=read+write

# Step 2: Exchange code for token
curl -X POST "https://your-instance.social/oauth/token" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=YOUR_REDIRECT_URI"
```

## Configuration

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/mastodon" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-mastodon-access-token",
      "instance_url": "https://mastodon.social"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    access_token="your-mastodon-access-token",
    extra={
        "instance_url": "https://mastodon.social",
    }
)
connector = get_connector("mastodon", config)
```

## Usage Examples

### Publish a Toot

```python
async with connector:
    result = await connector.publish(
        content="Hello Fediverse! 🐘",
        tags=["introduction", "mastodon"],
        visibility="public",
    )
    print(f"Post URL: {result.post_url}")
```

### Publish with Images

```python
result = await connector.publish(
    content="Check out this photo!",
    images=["./photo.jpg"],  # Local file path
    visibility="public",
)
```

### Content Warning (CW)

```python
result = await connector.publish(
    content="Detailed spoiler discussion here...",
    spoiler_text="Movie spoilers",  # Content warning
    visibility="public",
)
```

### Reply to a Toot

```python
result = await connector.publish(
    content="Great point! I agree.",
    in_reply_to_id="original_post_id",
)
```

### Visibility Options

```python
# Public - visible on public timelines
result = await connector.publish(content="Hello!", visibility="public")

# Unlisted - visible but not on public timelines
result = await connector.publish(content="Hello!", visibility="unlisted")

# Private - followers only
result = await connector.publish(content="Hello!", visibility="private")

# Direct - mentioned users only
result = await connector.publish(content="@user Hello!", visibility="direct")
```

### Fetch Trending Toots

```python
result = await connector.fetch_trending(limit=20)
for toot in result.data:
    print(f"@{toot['author']}: {toot['body'][:50]}")
```

### Search

```python
result = await connector.fetch_trending(query="AI", limit=10)
```

## Instance Selection

Choose an instance based on:

- **Topic focus**: Many instances have specific themes
- **Size**: Larger instances have more content, smaller ones more community
- **Rules**: Each instance has its own moderation policies

Popular instances:
- `mastodon.social` - General purpose
- `fosstodon.org` - Open source focus
- `techhub.social` - Technology focus
- `infosec.exchange` - Security focus

## API Response Fields

- `post_id`: Status ID
- `body`: Post content (HTML)
- `likes`: Favourites count
- `comments`: Replies count
- `shares`: Reblogs count
- `url`: Post permalink
- `visibility`: public, unlisted, private, direct

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/mastodon/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Instance not reachable"
- Check the instance URL is correct
- Verify the instance is online

### "Invalid token"
- Tokens may be revoked by user
- Regenerate access token in app settings

### "Media upload failed"
- Check file format (JPEG, PNG, GIF supported)
- Verify file size limits (varies by instance)

## Links

- [Mastodon Documentation](https://docs.joinmastodon.org/)
- [API Reference](https://docs.joinmastodon.org/api/)
- [Join Mastodon](https://joinmastodon.org/)
- [Instance Picker](https://instances.social/)
