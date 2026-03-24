# Brave Search Connector

Brave Search is a privacy-focused search engine with its own independent index. This is a read-only connector for web and news search.

## Platform Overview

- **Type**: Search engine (read-only)
- **Purpose**: Web and news search for topic discovery
- **API Type**: REST
- **Authentication**: API key

## Key Features

- **Privacy-focused**: No user tracking
- **Independent index**: Not relying on Google/Bing
- **Generous free tier**: 2,000 queries/month free
- **Fast responses**: Low latency API

## Prerequisites

1. Brave Search API account
2. API subscription (free tier available)
3. API key

## Getting API Key

### Step 1: Sign Up

1. Go to [Brave Search API](https://api.search.brave.com/)
2. Click **Get Started**
3. Create an account or sign in

### Step 2: Choose Plan

- **Free**: 2,000 queries/month
- **Basic**: 20,000 queries/month ($5/month)
- **Pro**: Custom pricing

### Step 3: Get API Key

1. Go to your dashboard
2. Find your API key
3. Copy the key securely

## Configuration

### Environment Variables

```bash
export BRAVE_SEARCH_API_KEY="your-api-key"
```

### Web Admin UI

1. Navigate to **Connectors** page
2. Click on **Brave Search**
3. Enter your API Key
4. Click **Save** then **Test Connection**

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/brave_search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "api_key": "your-brave-api-key"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    api_key="your-brave-api-key",
)
connector = get_connector("brave_search", config)
```

## Usage Examples

### Web Search

```python
async with connector:
    results = await connector.search(
        query="artificial intelligence trends 2024",
        limit=10,
        search_type="web",
    )
    for result in results:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Description: {result['description']}")
```

### News Search

```python
results = await connector.search(
    query="tech news",
    limit=10,
    search_type="news",
)
```

### Using for Topic Discovery

```python
# Search for trending topics in a niche
result = await connector.fetch_trending(query="AI tools", limit=20)
for item in result.data:
    print(f"- {item['title']}")
```

## Response Fields

- `id`: URL (used as unique identifier)
- `title`: Page/article title
- `description`: Content snippet
- `url`: Full URL to the content
- `source`: "brave_search" or "brave_search_news"
- `created_at`: Publication date (for news)

## Limitations

- **Read-only**: No publishing capability
- **Rate limits**: Based on subscription tier
- **No user content**: Cannot fetch user-specific data
- **Results per request**: Maximum 20

## Use Cases in AvatarFactory

1. **Topic Discovery**: Find trending topics not yet on social platforms
2. **Content Research**: Research background information for content
3. **Competitor Analysis**: Search for competitor mentions
4. **Trend Validation**: Cross-reference social trends with web search

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/brave_search/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Invalid API key"
- Verify the key is correct
- Check subscription is active

### "Rate limit exceeded"
- Check your monthly quota
- Upgrade plan if needed
- Implement request throttling

### "No results returned"
- Try different search terms
- Check query isn't too specific

## Links

- [Brave Search API](https://api.search.brave.com/)
- [API Documentation](https://api.search.brave.com/app/documentation/)
- [Pricing](https://api.search.brave.com/app/pricing)
