"""
Twitter/X platform connector.

Twitter API v2 requires OAuth 2.0 or OAuth 1.0a authentication.
Documentation: https://developer.twitter.com/en/docs/twitter-api
"""

from datetime import datetime
from typing import Any, List, Optional

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectionStatus,
    ConnectorCapabilities,
    ConnectorConfig,
    ConnectorConfigField,
    FetchResult,
    IntegrationType,
    PublishResult,
)
from avatarfactory.connectors.registry import ConnectorRegistry


@ConnectorRegistry.register_decorator("twitter")
@ConnectorRegistry.register_decorator("x")
class TwitterConnector(BasePlatformConnector):
    """Twitter/X platform connector using API v2"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._bearer_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._username: Optional[str] = None

    @property
    def platform_name(self) -> str:
        return "twitter"

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            platform="twitter",
            display_name="Twitter / X",
            description="Twitter/X API v2 with OAuth authentication",
            supports_topic_discovery=True,
            supports_persona_discovery=True,
            supports_publishing=True,
            supports_fetching=True,
            config_fields=[
                ConnectorConfigField(
                    name="api_key",
                    label="API Key",
                    field_type="text",
                    required=True,
                    description="Twitter API Key (Consumer Key)",
                    env_var="TWITTER_API_KEY",
                ),
                ConnectorConfigField(
                    name="api_secret",
                    label="API Secret",
                    field_type="password",
                    required=True,
                    description="Twitter API Secret (Consumer Secret)",
                    env_var="TWITTER_API_SECRET",
                ),
                ConnectorConfigField(
                    name="access_token",
                    label="Access Token",
                    field_type="password",
                    required=False,
                    description=("Bearer token for app-only access," " or OAuth access token"),
                    env_var="TWITTER_ACCESS_TOKEN",
                ),
                ConnectorConfigField(
                    name="access_token_secret",
                    label="Access Token Secret",
                    field_type="password",
                    required=False,
                    description=("OAuth access token secret" " (required for publishing)"),
                    env_var="TWITTER_ACCESS_TOKEN_SECRET",
                ),
            ],
            integration_type=IntegrationType.API,
            usage_guide=(
                "Use via ConnectorRegistry API. Supports two auth modes:"
                " (1) Bearer token for read-only trending/search via"
                " fetch_trending(), (2) OAuth 1.0a with all four keys for"
                " publishing via publish(). For topic discovery, use"
                " connector.fetch_trending(query) to search recent tweets."
                " For persona discovery, use"
                " connector.fetch_user_posts(user_id) to analyze a user's"
                " timeline. Rate limits apply per Twitter API v2 tiers."
            ),
        )

    async def connect(self) -> bool:
        """Connect to Twitter using OAuth 2.0 Bearer Token or API keys"""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx required for Twitter connector. Install with: pip install httpx"
            )

        # Twitter supports multiple auth methods
        # 1. Bearer Token (app-only, read-only)
        # 2. OAuth 1.0a (user context, read/write)
        # 3. OAuth 2.0 with PKCE (user context, read/write)

        if self.config.access_token:
            # Use Bearer Token for app-only access
            self._bearer_token = self.config.access_token
        elif self.config.api_key and self.config.api_secret:
            # Get Bearer Token using API key/secret
            self.status = ConnectionStatus.CONNECTING
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.twitter.com/oauth2/token",
                        auth=(self.config.api_key, self.config.api_secret),
                        data={"grant_type": "client_credentials"},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        self._bearer_token = data.get("access_token")
                    else:
                        raise ValueError(f"Failed to get bearer token: {response.text}")

            except Exception as e:
                self.status = ConnectionStatus.ERROR
                raise RuntimeError(f"Failed to authenticate with Twitter: {e}")
        else:
            raise ValueError(
                "Twitter requires either access_token (bearer token) or "
                "api_key + api_secret for authentication"
            )

        # Verify connection by getting authenticated user info
        self.status = ConnectionStatus.CONNECTING
        try:
            async with httpx.AsyncClient() as client:
                # Try to get authenticated user (only works with user context auth)
                response = await client.get(
                    "https://api.twitter.com/2/users/me",
                    headers={"Authorization": f"Bearer {self._bearer_token}"},
                )

                if response.status_code == 200:
                    data = response.json().get("data", {})
                    self._user_id = data.get("id")
                    self._username = data.get("username")
                elif response.status_code == 403:
                    # App-only auth doesn't have user context, but connection is valid
                    pass
                else:
                    # Connection is still valid for reading
                    pass

            self.status = ConnectionStatus.CONNECTED
            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise RuntimeError(f"Failed to connect to Twitter: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Twitter"""
        self._bearer_token = None
        self._user_id = None
        self._username = None
        self.status = ConnectionStatus.DISCONNECTED

    async def verify_credentials(self) -> bool:
        """Verify credentials are valid"""
        if not self._bearer_token:
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.twitter.com/2/users/me",
                    headers={"Authorization": f"Bearer {self._bearer_token}"},
                )
                # 200 = valid user auth, 403 = valid app auth (no user context)
                return response.status_code in (200, 403)
        except Exception:
            return False

    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """Publish a tweet to Twitter"""
        if not self.is_connected():
            return PublishResult(
                success=False,
                error="Not connected to Twitter",
                platform=self.platform_name,
            )

        # Check if we have user context (required for posting)
        if not self._user_id:
            return PublishResult(
                success=False,
                error="Publishing requires user context authentication (OAuth 1.0a or OAuth 2.0 with PKCE)",
                platform=self.platform_name,
            )

        try:
            import httpx

            # Build tweet text with hashtags
            tweet_text = content
            if tags:
                hashtags = " ".join(f"#{tag}" for tag in tags)
                tweet_text = f"{content}\n\n{hashtags}"

            # Twitter limit is 280 chars
            tweet_text = tweet_text[:280]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.twitter.com/2/tweets",
                    headers={
                        "Authorization": f"Bearer {self._bearer_token}",
                        "Content-Type": "application/json",
                    },
                    json={"text": tweet_text},
                )

                if response.status_code == 201:
                    data = response.json().get("data", {})
                    tweet_id = data.get("id", "")

                    return PublishResult(
                        success=True,
                        post_id=tweet_id,
                        post_url=f"https://twitter.com/{self._username}/status/{tweet_id}",
                        platform=self.platform_name,
                        published_at=datetime.utcnow(),
                        raw_response=data,
                    )
                else:
                    error_data = response.json()
                    error = error_data.get("detail", error_data.get("title", "Unknown error"))
                    return PublishResult(
                        success=False,
                        error=error,
                        platform=self.platform_name,
                    )

        except Exception as e:
            return PublishResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """Fetch trending/popular tweets from Twitter"""
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Twitter",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                if query:
                    # Search tweets
                    params = {
                        "query": query,
                        "max_results": min(limit, 100),
                        "tweet.fields": "created_at,public_metrics,author_id",
                        "expansions": "author_id",
                        "user.fields": "username",
                    }
                    response = await client.get(
                        "https://api.twitter.com/2/tweets/search/recent",
                        params=params,
                        headers={"Authorization": f"Bearer {self._bearer_token}"},
                    )
                else:
                    # Get home timeline (requires user context)
                    if not self._user_id:
                        return FetchResult(
                            success=False,
                            error="Timeline requires user context authentication",
                            platform=self.platform_name,
                        )

                    params = {
                        "max_results": min(limit, 100),
                        "tweet.fields": "created_at,public_metrics,author_id",
                        "expansions": "author_id",
                        "user.fields": "username",
                    }
                    response = await client.get(
                        f"https://api.twitter.com/2/users/{self._user_id}/timelines/reverse_chronological",
                        params=params,
                        headers={"Authorization": f"Bearer {self._bearer_token}"},
                    )

                if response.status_code == 200:
                    data = response.json()
                    tweets = data.get("data", [])
                    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

                    results = []
                    for tweet in tweets[:limit]:
                        author_id = tweet.get("author_id", "")
                        author = users.get(author_id, {})
                        metrics = tweet.get("public_metrics", {})

                        results.append(
                            {
                                "platform": self.platform_name,
                                "post_id": tweet.get("id", ""),
                                "author": author.get("username", ""),
                                "author_id": author_id,
                                "body": tweet.get("text", ""),
                                "likes": metrics.get("like_count", 0),
                                "comments": metrics.get("reply_count", 0),
                                "shares": metrics.get("retweet_count", 0),
                                "views": metrics.get("impression_count", 0),
                                "published_at": tweet.get("created_at"),
                                "url": f"https://twitter.com/{author.get('username')}/status/{tweet.get('id')}",
                            }
                        )

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                        cursor=data.get("meta", {}).get("next_token"),
                    )
                else:
                    error_data = response.json()
                    error = error_data.get("detail", error_data.get("title", "Unknown error"))
                    return FetchResult(
                        success=False,
                        error=error,
                        platform=self.platform_name,
                    )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )

    async def fetch_user_posts(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """Fetch tweets from a user"""
        if not self.is_connected():
            return FetchResult(
                success=False,
                error="Not connected to Twitter",
                platform=self.platform_name,
            )

        target_user = user_id or self._user_id
        if not target_user:
            return FetchResult(
                success=False,
                error="User ID required (no authenticated user context)",
                platform=self.platform_name,
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                params = {
                    "max_results": min(limit, 100),
                    "tweet.fields": "created_at,public_metrics",
                }
                response = await client.get(
                    f"https://api.twitter.com/2/users/{target_user}/tweets",
                    params=params,
                    headers={"Authorization": f"Bearer {self._bearer_token}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    tweets = data.get("data", [])

                    results = []
                    for tweet in tweets[:limit]:
                        metrics = tweet.get("public_metrics", {})

                        results.append(
                            {
                                "platform": self.platform_name,
                                "post_id": tweet.get("id", ""),
                                "author": self._username or "",
                                "author_id": target_user,
                                "body": tweet.get("text", ""),
                                "likes": metrics.get("like_count", 0),
                                "comments": metrics.get("reply_count", 0),
                                "shares": metrics.get("retweet_count", 0),
                                "published_at": tweet.get("created_at"),
                            }
                        )

                    return FetchResult(
                        success=True,
                        data=results,
                        platform=self.platform_name,
                        fetched_at=datetime.utcnow(),
                        cursor=data.get("meta", {}).get("next_token"),
                    )
                else:
                    error_data = response.json()
                    error = error_data.get("detail", error_data.get("title", "Unknown error"))
                    return FetchResult(
                        success=False,
                        error=error,
                        platform=self.platform_name,
                    )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e),
                platform=self.platform_name,
            )
