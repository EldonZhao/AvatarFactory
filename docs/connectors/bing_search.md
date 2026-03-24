# Bing Search Connector

Microsoft Bing Search provides web, news, and image search through Azure Cognitive Services. This is a read-only connector for search-based topic discovery.

## Platform Overview

- **Type**: Search engine (read-only)
- **Purpose**: Web, news, and image search
- **API Type**: REST
- **Authentication**: Azure Cognitive Services API key

## Key Features

- **Comprehensive search**: Web, news, and images
- **Market targeting**: Search results by region/language
- **Rich metadata**: Includes source info, dates, thumbnails
- **Enterprise-grade**: Azure reliability and support

## Prerequisites

1. Azure account
2. Bing Search resource in Azure
3. API key from Azure portal

## Getting API Key

### Step 1: Create Azure Account

1. Go to [Azure Portal](https://portal.azure.com/)
2. Create an account if you don't have one
3. Set up billing (free tier available)

### Step 2: Create Bing Search Resource

1. In Azure Portal, click **Create a resource**
2. Search for "Bing Search"
3. Select **Bing Search v7**
4. Fill in details:
   - Subscription
   - Resource group (create new or use existing)
   - Name
   - Pricing tier (F0 for free tier)
5. Click **Create**

### Step 3: Get API Key

1. Go to your Bing Search resource
2. Click **Keys and Endpoint**
3. Copy **Key 1** or **Key 2**
4. Note the endpoint URL

## Configuration

### Environment Variables

```bash
export BING_SEARCH_API_KEY="your-azure-api-key"
export BING_SEARCH_ENDPOINT="https://api.bing.microsoft.com/v7.0"  # Optional
```

### Web Admin UI

1. Navigate to **Connectors** page
2. Click on **Bing Search**
3. Enter your API Key
4. Optionally enter custom endpoint
5. Click **Save** then **Test Connection**

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/bing_search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "api_key": "your-bing-api-key"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    api_key="your-bing-api-key",
)
connector = get_connector("bing_search", config)
```

## Usage Examples

### Web Search

```python
async with connector:
    results = await connector.search(
        query="machine learning trends",
        limit=20,
        search_type="web",
        market="en-US",
    )
    for result in results:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
```

### News Search

```python
results = await connector.search(
    query="AI startups",
    limit=10,
    search_type="news",
    market="en-US",
)
for item in results:
    print(f"Title: {item['title']}")
    print(f"Provider: {item.get('provider', 'Unknown')}")
    print(f"Date: {item.get('created_at')}")
```

### Image Search

```python
results = await connector.search(
    query="modern office design",
    limit=10,
    search_type="images",
)
for image in results:
    print(f"Title: {image['title']}")
    print(f"Thumbnail: {image.get('thumbnail_url')}")
```

### Market Targeting

```python
# Chinese market
results = await connector.search(
    query="人工智能",
    market="zh-CN",
)

# UK market
results = await connector.search(
    query="tech news",
    market="en-GB",
)
```

## Search Types

### Web Search
- General web page results
- Includes URL, title, snippet
- `dateLastCrawled` for freshness

### News Search
- Recent news articles
- Includes provider name
- `datePublished` for exact timing

### Image Search
- Image results with metadata
- Includes thumbnail URLs
- Host page information

## Response Fields

### Web Results
- `id`: URL
- `title`: Page title
- `description`: Snippet
- `url`: Full URL
- `created_at`: Last crawled date

### News Results
- `id`: URL
- `title`: Article title
- `description`: Article description
- `url`: Article URL
- `provider`: News source name
- `created_at`: Publication date

### Image Results
- `id`: Content URL
- `title`: Image name
- `url`: Host page URL
- `thumbnail_url`: Thumbnail URL

## Market Codes

Common market codes:
- `en-US` - English (United States)
- `en-GB` - English (United Kingdom)
- `zh-CN` - Chinese (China)
- `ja-JP` - Japanese (Japan)
- `de-DE` - German (Germany)
- `fr-FR` - French (France)

## Pricing Tiers

| Tier | Calls/Month | Price |
|------|-------------|-------|
| F0 (Free) | 1,000 | $0 |
| S1 | 1,000 | $7/month |
| S2 | 10,000 | $3/1,000 calls |

## Limitations

- **Read-only**: No publishing capability
- **Rate limits**: Based on subscription tier
- **Results per request**: Maximum 50
- **No user content**: Cannot fetch user-specific data

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/bing_search/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Invalid subscription key"
- Verify the key is correct
- Check the resource is active in Azure

### "Rate limit exceeded"
- Check quota in Azure portal
- Upgrade pricing tier if needed

### "Endpoint not found"
- Verify endpoint URL is correct
- Use default endpoint if unsure

## Links

- [Bing Search API Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/bing-web-search/)
- [Azure Portal](https://portal.azure.com/)
- [Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/search-api/)
