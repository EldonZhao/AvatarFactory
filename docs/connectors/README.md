# Platform Connectors

AvatarFactory supports multiple social media platforms through its connector system. Each connector handles authentication, content publishing, and data fetching for a specific platform.

## Available Connectors

| Platform | Connector | Status | Complexity | Notes |
|----------|-----------|--------|------------|-------|
| [Bluesky](bluesky.md) | `bluesky` / `bsky` | ✅ Stable | Low | AT Protocol, simple app password auth |
| [Twitter/X](twitter.md) | `twitter` | ✅ Stable | Medium | OAuth 2.0, API v2 |
| [Xiaohongshu](xiaohongshu.md) | `xiaohongshu` / `xhs` | ✅ Stable | High | Cookie-based auth, xhs signing |
| [LinkedIn](linkedin.md) | `linkedin` | ✅ New | Medium | OAuth 2.0, professional network |
| [Threads](threads.md) | `threads` | ✅ New | Medium | Meta Graph API |
| [Instagram](instagram.md) | `instagram` / `ig` | ✅ New | High | Meta Graph API, business accounts only |
| [Weibo](weibo.md) | `weibo` | ✅ New | Medium | OAuth 2.0, Chinese market |
| [Mastodon](mastodon.md) | `mastodon` | ✅ New | Low | Simple REST API, any instance |
| [Toutiao](toutiao.md) | `toutiao` | ✅ New | Medium | OAuth 2.0, Chinese news platform |
| [WeCom](wecom.md) | `wecom` | ✅ Stable | Low | Webhook notifications |

### Search Connectors (Read-Only)

| Platform | Connector | Status | Notes |
|----------|-----------|--------|-------|
| [Brave Search](brave_search.md) | `brave_search` | ✅ Stable | Privacy-focused web search |
| [Bing Search](bing_search.md) | `bing_search` | ✅ Stable | Azure Cognitive Services |
| [Zhihu](zhihu.md) | `zhihu` | ✅ New | Chinese Q&A platform, cookie-based |

## Quick Start

### 1. Web Admin UI (Recommended)

Navigate to the **Connectors** page in the Admin dashboard:

1. Go to `http://localhost:4321/connectors`
2. Click on any connector card
3. Fill in the required credentials
4. Click **Save** to store the configuration
5. Click **Test Connection** to verify

### 2. Environment Variables (Simple Mode)

For single-tenant deployments, configure connectors via environment variables:

```bash
# Bluesky
export BLUESKY_USERNAME="your-handle.bsky.social"
export BLUESKY_PASSWORD="your-app-password"

# Twitter
export TWITTER_API_KEY="your-api-key"
export TWITTER_API_SECRET="your-api-secret"
export TWITTER_ACCESS_TOKEN="your-access-token"
export TWITTER_ACCESS_TOKEN_SECRET="your-access-token-secret"
```

### 3. Multi-Tenant Mode

For multi-tenant deployments, configure connectors per-tenant via the API:

```bash
# Configure connector for a tenant
curl -X PUT "http://localhost:8000/tenant/connectors/bluesky" \
  -H "X-API-Key: your-tenant-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "username": "your-handle.bsky.social",
      "password": "your-app-password"
    }
  }'

# Test the connection
curl -X POST "http://localhost:8000/tenant/connectors/bluesky/test" \
  -H "X-API-Key: your-tenant-api-key"
```

### 4. Using Connectors in Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

# Create connector with config
config = ConnectorConfig(
    username="your-handle.bsky.social",
    password="your-app-password",
)
connector = get_connector("bluesky", config)

# Use async context manager
async with connector:
    # Publish content
    result = await connector.publish(
        content="Hello from AvatarFactory!",
        tags=["ai", "content"],
    )
    print(f"Published: {result.post_url}")

    # Fetch trending content
    trending = await connector.fetch_trending(limit=10)
    for post in trending.data:
        print(f"- {post['body'][:50]}...")
```

## Connector Architecture

All connectors inherit from `BasePlatformConnector` and implement:

- `connect()` - Establish connection/authenticate
- `disconnect()` - Clean up connection
- `verify_credentials()` - Check if credentials are valid
- `publish()` - Publish content to the platform
- `fetch_trending()` - Fetch trending/popular content
- `fetch_user_posts()` - Fetch posts from a specific user

### Registration

Connectors are registered using the decorator pattern:

```python
from avatarfactory.connectors.base import BasePlatformConnector
from avatarfactory.connectors.registry import ConnectorRegistry

@ConnectorRegistry.register_decorator("myplatform")
class MyPlatformConnector(BasePlatformConnector):
    @property
    def platform_name(self) -> str:
        return "myplatform"

    async def connect(self) -> bool:
        # Implementation
        pass

    # ... other methods
```

## Adding a New Connector

1. Create a new file in `avatarfactory/connectors/` (e.g., `myplatform.py`)
2. Implement the `BasePlatformConnector` interface
3. Register with `@ConnectorRegistry.register_decorator("myplatform")`
4. Import in `avatarfactory/connectors/__init__.py`
5. Create documentation in `docs/connectors/myplatform.md`

See individual connector documentation for platform-specific details.

## Error Handling

All connector operations return result objects with success status:

```python
result = await connector.publish(content="Hello")

if result.success:
    print(f"Posted: {result.post_url}")
else:
    print(f"Error: {result.error}")
```

## Rate Limiting

Connectors do not implement rate limiting internally. When using connectors in production:

1. Implement rate limiting at the application level
2. Respect platform-specific rate limits
3. Use exponential backoff for retries
