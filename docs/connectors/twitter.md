# Twitter/X Connector

Twitter (now X) is a microblogging platform. The connector uses Twitter API v2 with OAuth 2.0.

## Platform Overview

- **Type**: Microblogging
- **Character Limit**: 280 characters (basic), 4,000+ (Premium)
- **Image Support**: Up to 4 images per tweet
- **API Type**: REST (API v2)
- **Authentication**: OAuth 2.0 / OAuth 1.0a

## Prerequisites

1. Twitter/X account
2. Twitter Developer Account
3. Twitter App with API v2 access
4. OAuth credentials

## Getting API Credentials

### Step 1: Apply for Developer Account

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Sign up for a developer account
3. Describe your use case
4. Wait for approval

### Step 2: Create a Project and App

1. Go to **Projects & Apps** → **Overview**
2. Create a new Project
3. Create an App within the project
4. Note your credentials

### Step 3: Generate Keys

In your App settings:

1. Go to **Keys and tokens**
2. Generate:
   - **API Key** (Consumer Key)
   - **API Secret** (Consumer Secret)
   - **Access Token**
   - **Access Token Secret**

For OAuth 2.0 (App-only):
- **Bearer Token**

## Configuration

### Environment Variables

```bash
export TWITTER_API_KEY="your-api-key"
export TWITTER_API_SECRET="your-api-secret"
export TWITTER_ACCESS_TOKEN="your-access-token"
export TWITTER_ACCESS_TOKEN_SECRET="your-access-token-secret"
export TWITTER_BEARER_TOKEN="your-bearer-token"  # Optional
```

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/twitter" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "api_key": "your-twitter-api-key",
      "api_secret": "your-twitter-api-secret",
      "access_token": "your-access-token",
      "access_token_secret": "your-access-token-secret"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    api_key="your-api-key",
    api_secret="your-api-secret",
    access_token="your-access-token",
    access_token_secret="your-access-token-secret",
)
connector = get_connector("twitter", config)
```

## Usage Examples

### Publish a Tweet

```python
async with connector:
    result = await connector.publish(
        content="Hello Twitter! 🐦",
        tags=["hello", "ai"],
    )
    print(f"Tweet URL: {result.post_url}")
```

### Tweet with Images

```python
result = await connector.publish(
    content="Check this out!",
    images=["./image1.jpg", "./image2.jpg"],
)
```

### Fetch Trending

```python
result = await connector.fetch_trending(limit=20)
for tweet in result.data:
    print(f"@{tweet['author']}: {tweet['body'][:50]}")
```

### Search Tweets

```python
result = await connector.search(query="AI tools", limit=10)
```

## API Access Tiers

Twitter has different access tiers:

| Tier | Tweets/Month | Price | Features |
|------|--------------|-------|----------|
| Free | 1,500 | $0 | Post, Delete |
| Basic | 3,000 | $100/mo | + Read, Search |
| Pro | 300,000 | $5,000/mo | + Full archive |

## API Response Fields

- `post_id`: Tweet ID
- `body`: Tweet text
- `likes`: Like count
- `comments`: Reply count
- `shares`: Retweet count
- `url`: Tweet permalink

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/twitter/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Authentication failed"
- Verify all four OAuth credentials are correct
- Check API keys are for the right project

### "Rate limit exceeded"
- Twitter has strict rate limits
- Implement backoff logic

### "Forbidden"
- Check your API tier supports the requested action
- Some features require paid tiers

## Links

- [Twitter Developer Portal](https://developer.twitter.com/)
- [API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [OAuth 2.0 Guide](https://developer.twitter.com/en/docs/authentication/oauth-2-0)
