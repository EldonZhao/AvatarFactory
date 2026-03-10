"""
Base platform connector for AvatarFactory.

Provides abstract interface for all platform connectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConnectionStatus(str, Enum):
    """Connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class IntegrationType(str, Enum):
    """How sub-agents integrate with this connector"""
    API = "api"
    AGENT_SKILL = "agent_skill"
    MCP_TOOL = "mcp_tool"


class ConnectorConfigField(BaseModel):
    """Schema for a single connector configuration field (for frontend rendering)."""
    name: str = Field(..., description="Field name used as the key in credentials dict")
    label: str = Field(..., description="Human-readable label for UI display")
    field_type: str = Field(
        default="text",
        description="Input type: text, password, textarea, url, email, number",
    )
    required: bool = Field(default=False, description="Whether this field is required")
    description: str = Field(default="", description="Help text for the field")
    placeholder: str = Field(default="", description="Placeholder text for the input")
    env_var: Optional[str] = Field(
        default=None,
        description="Environment variable that can be used as fallback",
    )


class ConnectorCapabilities(BaseModel):
    """Describes the capabilities and metadata of a connector."""
    platform: str = Field(..., description="Platform identifier")
    display_name: str = Field(..., description="Human-readable platform name")
    description: str = Field(default="", description="Short description of the connector")

    # Discovery capability flags
    supports_topic_discovery: bool = Field(
        default=False,
        description="Whether this connector can be used for topic/trend mining",
    )
    supports_persona_discovery: bool = Field(
        default=False,
        description="Whether this connector can be used for persona/audience mining",
    )

    # Functional capability flags
    supports_publishing: bool = Field(
        default=False,
        description="Whether this connector can publish content",
    )
    supports_fetching: bool = Field(
        default=False,
        description="Whether this connector can fetch/search content",
    )

    # Frontend config schema
    config_fields: List[ConnectorConfigField] = Field(
        default_factory=list,
        description="Configuration fields needed by this connector (for frontend forms)",
    )

    # Integration info for sub-agents
    integration_type: IntegrationType = Field(
        default=IntegrationType.API,
        description="Primary integration method for sub-agents",
    )
    usage_guide: str = Field(
        default="",
        description="Detailed usage instructions for sub-agents",
    )


class ConnectorConfig(BaseModel):
    """Configuration for platform connector"""
    # Common fields
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None

    # OAuth fields
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None

    # App password (for Bluesky)
    username: Optional[str] = None
    password: Optional[str] = None

    # MCP/Skills integration
    use_mcp: bool = False
    mcp_server_name: Optional[str] = None

    # Additional platform-specific config
    extra: Dict[str, Any] = field(default_factory=dict)

    class Config:
        extra = "allow"


class PublishResult(BaseModel):
    """Result of publishing content"""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    platform: str = ""
    published_at: Optional[datetime] = None
    raw_response: Optional[Dict[str, Any]] = None


class FetchResult(BaseModel):
    """Result of fetching content"""
    success: bool
    data: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    platform: str = ""
    fetched_at: Optional[datetime] = None
    cursor: Optional[str] = None  # For pagination

    class Config:
        arbitrary_types_allowed = True


class TrendingContent(BaseModel):
    """Trending/popular content from platform"""
    platform: str
    post_id: str
    author: str
    author_id: Optional[str] = None
    title: Optional[str] = None
    body: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    tags: List[str] = field(default_factory=list)
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.now)


class BasePlatformConnector(ABC):
    """Base class for all platform connectors"""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._client: Any = None

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform name"""
        pass

    @classmethod
    def get_capabilities(cls) -> ConnectorCapabilities:
        """
        Return the capabilities and metadata for this connector.

        Subclasses should override this to provide platform-specific capabilities
        including config fields for frontend rendering, discovery flags, and
        integration guides for sub-agents.

        Returns:
            ConnectorCapabilities describing this connector
        """
        return ConnectorCapabilities(
            platform="unknown",
            display_name="Unknown",
            description="Base connector with no specific capabilities.",
        )

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to platform.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from platform"""
        pass

    @abstractmethod
    async def verify_credentials(self) -> bool:
        """
        Verify that credentials are valid.

        Returns:
            True if credentials are valid
        """
        pass

    @abstractmethod
    async def publish(
        self,
        content: str,
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> PublishResult:
        """
        Publish content to platform.

        Args:
            content: Main content text
            title: Optional title (for platforms that support it)
            images: Optional list of image paths/URLs
            tags: Optional list of hashtags
            **kwargs: Platform-specific options

        Returns:
            PublishResult with success status and post details
        """
        pass

    @abstractmethod
    async def fetch_trending(
        self,
        query: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch trending/popular content.

        Args:
            query: Optional search query
            limit: Maximum number of results
            **kwargs: Platform-specific options

        Returns:
            FetchResult with list of trending content
        """
        pass

    @abstractmethod
    async def fetch_user_posts(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Fetch posts from a user (or authenticated user if user_id is None).

        Args:
            user_id: Optional user ID (defaults to authenticated user)
            limit: Maximum number of results
            **kwargs: Platform-specific options

        Returns:
            FetchResult with list of posts
        """
        pass

    async def search(
        self,
        query: str,
        limit: int = 20,
        **kwargs: Any,
    ) -> FetchResult:
        """
        Search for content.

        Args:
            query: Search query
            limit: Maximum number of results
            **kwargs: Platform-specific options

        Returns:
            FetchResult with search results
        """
        # Default implementation uses fetch_trending with query
        return await self.fetch_trending(query=query, limit=limit, **kwargs)

    def is_connected(self) -> bool:
        """Check if connector is connected"""
        return self.status == ConnectionStatus.CONNECTED

    async def __aenter__(self) -> "BasePlatformConnector":
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.disconnect()
