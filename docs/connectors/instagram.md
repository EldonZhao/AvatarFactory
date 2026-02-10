# Instagram Connector

Instagram is a visual-first social platform. The connector supports posting images and carousels to Instagram Business or Creator accounts.

## Platform Overview

- **Type**: Visual social network
- **Content**: Images/videos required (no text-only posts)
- **Caption Limit**: 2,200 characters
- **Image Support**: Up to 10 images per carousel
- **API Type**: Meta Graph API
- **Authentication**: OAuth 2.0 via Meta

## Prerequisites

1. **Instagram Business or Creator account** (personal accounts not supported)
2. Facebook Page connected to your Instagram account
3. Meta Developer App with Instagram Graph API access
4. OAuth 2.0 access token

## Account Setup

### Convert to Business Account

1. Go to Instagram → Settings → Account
2. Select **Switch to Professional Account**
3. Choose **Business** or **Creator**
4. Connect to a Facebook Page

## Getting API Credentials

### Step 1: Create a Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app (Business type)
3. Add **Instagram Graph API** product

### Step 2: Get Instagram Business Account ID

```bash
# Get Facebook Pages
curl "https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_TOKEN"

# Get Instagram Business Account from Page
curl "https://graph.facebook.com/v18.0/PAGE_ID?
  fields=instagram_business_account&
  access_token=YOUR_TOKEN"
```

### Step 3: Get Access Token

Use the Facebook OAuth flow:

```bash
# Authorization URL
https://www.facebook.com/v18.0/dialog/oauth?
  client_id=YOUR_APP_ID&
  redirect_uri=YOUR_REDIRECT_URI&
  scope=instagram_basic,instagram_content_publish,pages_read_engagement
```

## Configuration

### Multi-Tenant API

```bash
curl -X PUT "http://localhost:8000/tenant/connectors/instagram" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "access_token": "your-meta-access-token",
      "instagram_business_account_id": "your-ig-account-id"
    }
  }'
```

### Python Code

```python
from avatarfactory.connectors import get_connector, ConnectorConfig

config = ConnectorConfig(
    access_token="your-meta-access-token",
    extra={
        "instagram_business_account_id": "your-ig-account-id",
    }
)
connector = get_connector("instagram", config)
```

## Usage Examples

### Publish Single Image

```python
async with connector:
    result = await connector.publish(
        content="Amazing sunset view! 🌅",
        images=["https://example.com/sunset.jpg"],  # Must be public URL
        tags=["sunset", "nature", "photography"],
    )
    print(f"Post URL: {result.post_url}")
```

### Publish Carousel

```python
result = await connector.publish(
    content="My travel highlights from Japan 🇯🇵",
    images=[
        "https://example.com/tokyo.jpg",
        "https://example.com/kyoto.jpg",
        "https://example.com/osaka.jpg",
    ],
    tags=["japan", "travel", "adventure"],
)
```

## Image Requirements

- **Format**: JPEG recommended
- **Size**: Max 8MB per image
- **Aspect Ratio**: 4:5 to 1.91:1
- **URL**: Must be publicly accessible (HTTPS recommended)

## Publishing Flow

Instagram uses a multi-step process:

1. **Create media container(s)**: Upload image references
2. **Create carousel container** (if multiple images)
3. **Publish container**: Actually publish the post

The connector handles this automatically.

## Limitations

- **No text-only posts**: At least one image required
- **No direct image upload**: Images must be hosted at public URLs
- **Business accounts only**: Personal accounts not supported
- **No hashtag search**: Limited discovery capabilities

## API Response Fields

- `post_id`: Instagram media ID
- `caption`: Post caption
- `likes`: Like count
- `comments`: Comment count
- `url`: Post permalink
- `media_type`: IMAGE, CAROUSEL_ALBUM, etc.

## Verification

```bash
curl -X POST "http://localhost:8000/tenant/connectors/instagram/test" \
  -H "X-API-Key: your-api-key"
```

## Troubleshooting

### "Container creation failed"
- Ensure images are publicly accessible via HTTPS
- Check image format and size requirements

### "Account not found"
- Verify you have a Business/Creator account
- Ensure the Facebook Page is connected

### "Permission denied"
- Request all necessary permissions in OAuth scope
- Check app review status for permissions

## Links

- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)
- [Content Publishing Guide](https://developers.facebook.com/docs/instagram-api/guides/content-publishing)
- [Meta for Developers](https://developers.facebook.com/)
