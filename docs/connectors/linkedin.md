# LinkedIn Connector

LinkedIn is a professional networking platform. The connector supports posting updates and articles to personal profiles or company pages.

## Platform Overview

- **Type**: Professional networking
- **Character Limit**: 3,000 characters per post
- **Image Support**: Yes (via URL)
- **API Type**: REST (OAuth 2.0)
- **Authentication**: OAuth 2.0 with access token

## Prerequisites

1. LinkedIn account
2. LinkedIn Developer App
3. OAuth 2.0 access token with appropriate permissions

## Getting API Credentials

### Step 1: Create a LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Click **Create App**
3. Fill in the required information:
   - App name
   - LinkedIn Page (create one if needed)
   - App logo
4. Accept the terms and create the app

### Step 2: Configure OAuth 2.0

1. In your app settings, go to **Auth** tab
2. Add OAuth 2.0 redirect URLs (e.g., `http://localhost:8000/callback`)
3. Note your **Client ID** and **Client Secret**

### Step 3: Request API Products

1. Go to **Products** tab
2. Request access to:
   - **Share on LinkedIn** (for posting)
   - **Sign In with LinkedIn using OpenID Connect** (for auth)
3. Wait for approval (may take a few days)

### Step 4: Get Access Token

Use OAuth 2.0 flow to obtain an access token:

```bash
# Step 1: Authorization URL (redirect user here)
https://www.linkedin.com/oauth/v2/authorization?
  response_type=code&
  client_id=YOUR_CLIENT_ID&
  redirect_uri=YOUR_REDIRECT_URI&
  scope=openid%20profile%20w_member_social

# Step 2: Exchange code for token
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=YOUR_REDIRECT_URI" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## Configuration

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/linkedin" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-oauth-access-token"
    }
  }'
```

### For Company Pages

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/linkedin" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-oauth-access-token",
      "organization_id": "your-company-page-id"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    access_token="your-oauth-access-token",
    extra={
        "organization_id": "your-company-page-id",  # Optional
    }
)
connector = get_connector("linkedin", config)
```

## Usage Examples

### Publish a Post

```python
async with connector:
    result = await connector.publish(
        content="Excited to share our latest AI research findings! 🚀",
        tags=["AI", "MachineLearning", "Research"],
        visibility="PUBLIC",  # PUBLIC, CONNECTIONS, or LOGGED_IN
    )
    print(f"Post URL: {result.post_url}")
```

### Post as Company Page

```python
result = await connector.publish(
    content="Company announcement...",
    as_organization=True,  # Requires organization_id in config
)
```

## Visibility Options

- `PUBLIC`: Visible to everyone
- `CONNECTIONS`: Visible to 1st-degree connections
- `LOGGED_IN`: Visible to any logged-in LinkedIn member

## API Limitations

LinkedIn API has significant restrictions for non-partner apps:

1. **No public search**: Cannot search for posts by keyword
2. **Limited content fetching**: Can only access authenticated user's content
3. **Rate limits**: 100 calls per day for most endpoints
4. **Token expiration**: Access tokens expire after 60 days

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/linkedin/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Authentication failed"
- Ensure access token is valid and not expired
- Check that required API products are approved

### "Insufficient permissions"
- Request the appropriate OAuth scopes
- Ensure "Share on LinkedIn" product is approved

### "403 Forbidden"
- Your app may not have the required permissions
- Contact LinkedIn support for API access

## Links

- [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
- [LinkedIn API Documentation](https://learn.microsoft.com/en-us/linkedin/)
- [OAuth 2.0 Guide](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
