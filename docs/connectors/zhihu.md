# Zhihu (知乎) Connector

Zhihu is China's leading Q&A and knowledge-sharing platform, similar to Quora. This connector supports topic and persona discovery through cookie-based authentication.

## Platform Overview

- **Type**: Q&A / Knowledge platform
- **Content Types**: Questions, Answers, Articles
- **API Type**: Private (cookie-based)
- **Authentication**: Browser cookies
- **Publishing**: Not supported (read-only)

## Key Features

- **Topic Discovery**: Find trending questions and topics
- **Persona Research**: Analyze expert content and profiles
- **Professional Content**: High-quality answers from domain experts
- **Hot Topics**: Real-time trending topics list

## Prerequisites

1. Zhihu account (registered and logged in)
2. Browser cookies (extracted from logged-in session)
3. User ID (optional, for specific user content)

## Getting Credentials

### Step 1: Log in to Zhihu

1. Open [zhihu.com](https://www.zhihu.com/) in your browser
2. Log in with your account
3. Ensure session is active

### Step 2: Extract Cookies

Using browser developer tools:

1. Open DevTools (F12 or right-click → Inspect)
2. Go to **Application** → **Cookies** → `zhihu.com`
3. Copy all cookies as a single string

**Method 1: Manual Copy**
```
z_c0=xxx; d_c0=xxx; _zap=xxx; ...
```

**Method 2: Using DevTools Console**
```javascript
document.cookie
```

### Step 3: Get User ID (Optional)

1. Go to your Zhihu profile
2. URL format: `zhihu.com/people/YOUR_URL_TOKEN`
3. Copy the URL token (e.g., `zhang-san-12`)

## Configuration

### Environment Variables

```bash
export ZHIHU_COOKIE="z_c0=xxx; d_c0=xxx; _zap=xxx; ..."
export ZHIHU_USER_ID="your-url-token"  # Optional
```

### Web Admin UI

1. Navigate to **Connectors** page
2. Click on **Zhihu**
3. Paste your cookie string
4. Optionally enter User URL Token
5. Click **Save** then **Test Connection**

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/zhihu" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "cookie": "z_c0=xxx; d_c0=xxx; ...",
      "user_id": "your-url-token"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    extra={
        "cookie": "z_c0=xxx; d_c0=xxx; ...",
        "user_id": "your-url-token",
    }
)
connector = get_connector("zhihu", config)
```

## Usage Examples

### Fetch Hot Questions

```python
async with connector:
    result = await connector.fetch_trending(limit=20)
    for item in result.data:
        print(f"Q: {item['title']}")
        print(f"   Answers: {item.get('answer_count', 0)}")
        print(f"   URL: {item['url']}")
```

### Fetch Hot Topics

```python
result = await connector.fetch_hot_topics(limit=50)
for topic in result.data:
    print(f"🔥 {topic['title']}")
    print(f"   Heat: {topic.get('heat', 'N/A')}")
```

### Search Questions

```python
result = await connector.fetch_trending(query="人工智能", limit=10)
for item in result.data:
    print(f"Type: {item['source']}")
    print(f"Title: {item['title']}")
```

### Search with Content Type

```python
# Search for answers
results = await connector.search(
    query="机器学习",
    content_type="answer",
    limit=10,
)

# Search for articles
results = await connector.search(
    query="深度学习",
    content_type="article",
    limit=10,
)
```

## Response Fields

### Questions
- `id`: Question ID
- `title`: Question title
- `description`: Question excerpt
- `url`: Question URL
- `answer_count`: Number of answers
- `follower_count`: Number of followers

### Answers
- `id`: Answer ID
- `title`: Question title
- `description`: Answer excerpt
- `author`: Author name
- `voteup_count`: Upvote count
- `comment_count`: Comment count

### Articles
- `id`: Article ID
- `title`: Article title
- `description`: Article excerpt
- `author`: Author name
- `voteup_count`: Upvote count

## Use Cases in AvatarFactory

1. **Topic Discovery**: Find trending topics in specific domains
2. **Persona Research**: Analyze expert answers for voice/style
3. **Content Ideas**: Discover frequently asked questions
4. **Audience Insights**: Understand pain points from questions

## Limitations

- **Read-only**: Publishing not supported
- **Cookie expiration**: Cookies expire periodically
- **Rate limits**: Avoid excessive requests
- **Authentication complexity**: Requires cookie refresh

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/zhihu/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Cookie expired"
- Re-extract cookies from a fresh browser session
- Log in again and update cookies

### "Rate limited / Blocked"
- Reduce request frequency
- Wait before retrying
- Cookies may be flagged; try new session

### "Content not found"
- Check if content is public
- Some content may require specific access

### "Authentication failed"
- Verify cookie string format is correct
- Ensure all required cookies are included

## Security Considerations

1. **Cookie safety**: Store cookies securely (encrypted)
2. **Session lifespan**: Cookies may expire, plan for refresh
3. **TOS compliance**: Review Zhihu terms of service
4. **Rate limiting**: Respect platform limits

## Links

- [Zhihu](https://www.zhihu.com/)
- [Zhihu Help Center](https://www.zhihu.com/help)
