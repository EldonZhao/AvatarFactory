"""
Unit tests for connector capabilities system.

Tests the ConnectorCapabilities model, get_capabilities() on connectors,
and ConnectorRegistry capability query methods.
"""

import pytest

from avatarfactory.connectors.base import (
    BasePlatformConnector,
    ConnectorCapabilities,
    ConnectorConfigField,
    ConnectorConfig,
    IntegrationType,
)
from avatarfactory.connectors.registry import ConnectorRegistry


class TestConnectorCapabilitiesModel:
    """Test the ConnectorCapabilities Pydantic model."""

    def test_minimal_capabilities(self):
        """Test creating capabilities with minimal fields."""
        caps = ConnectorCapabilities(
            platform="test",
            display_name="Test",
        )
        assert caps.platform == "test"
        assert caps.display_name == "Test"
        assert caps.supports_topic_discovery is False
        assert caps.supports_persona_discovery is False
        assert caps.supports_publishing is False
        assert caps.supports_fetching is False
        assert caps.config_fields == []
        assert caps.integration_type == IntegrationType.API
        assert caps.usage_guide == ""

    def test_full_capabilities(self):
        """Test creating capabilities with all fields."""
        caps = ConnectorCapabilities(
            platform="test",
            display_name="Test Platform",
            description="A test platform",
            supports_topic_discovery=True,
            supports_persona_discovery=True,
            supports_publishing=True,
            supports_fetching=True,
            config_fields=[
                ConnectorConfigField(
                    name="api_key",
                    label="API Key",
                    field_type="password",
                    required=True,
                    description="Your API key",
                    placeholder="Enter key",
                    env_var="TEST_API_KEY",
                ),
            ],
            integration_type=IntegrationType.MCP_TOOL,
            usage_guide="Use this connector via MCP.",
        )
        assert caps.supports_topic_discovery is True
        assert caps.supports_persona_discovery is True
        assert caps.supports_publishing is True
        assert caps.supports_fetching is True
        assert len(caps.config_fields) == 1
        assert caps.config_fields[0].name == "api_key"
        assert caps.config_fields[0].required is True
        assert caps.integration_type == IntegrationType.MCP_TOOL

    def test_capabilities_serialization(self):
        """Test capabilities can be serialized to dict."""
        caps = ConnectorCapabilities(
            platform="test",
            display_name="Test",
            config_fields=[
                ConnectorConfigField(
                    name="token",
                    label="Token",
                    required=True,
                    env_var="TEST_TOKEN",
                ),
            ],
        )
        data = caps.model_dump()
        assert data["platform"] == "test"
        assert len(data["config_fields"]) == 1
        assert data["config_fields"][0]["name"] == "token"
        assert data["integration_type"] == "api"


class TestConnectorConfigField:
    """Test the ConnectorConfigField model."""

    def test_minimal_field(self):
        """Test creating a config field with minimal info."""
        field = ConnectorConfigField(name="key", label="Key")
        assert field.name == "key"
        assert field.label == "Key"
        assert field.field_type == "text"
        assert field.required is False
        assert field.env_var is None

    def test_password_field(self):
        """Test creating a password config field."""
        field = ConnectorConfigField(
            name="secret",
            label="Secret",
            field_type="password",
            required=True,
            description="Enter your secret",
            env_var="MY_SECRET",
        )
        assert field.field_type == "password"
        assert field.required is True
        assert field.env_var == "MY_SECRET"


class TestIntegrationType:
    """Test IntegrationType enum."""

    def test_enum_values(self):
        """Test all integration types exist."""
        assert IntegrationType.API == "api"
        assert IntegrationType.AGENT_SKILL == "agent_skill"
        assert IntegrationType.MCP_TOOL == "mcp_tool"


class TestConnectorGetCapabilities:
    """Test get_capabilities() on actual connector classes."""

    def test_bluesky_capabilities(self):
        """Test Bluesky connector capabilities."""
        from avatarfactory.connectors.bluesky import BlueskyConnector

        caps = BlueskyConnector.get_capabilities()
        assert caps.platform == "bluesky"
        assert caps.supports_topic_discovery is True
        assert caps.supports_persona_discovery is True
        assert caps.supports_publishing is True
        assert caps.supports_fetching is True
        assert len(caps.config_fields) >= 2
        field_names = [f.name for f in caps.config_fields]
        assert "username" in field_names
        assert "password" in field_names
        assert caps.usage_guide != ""

    def test_twitter_capabilities(self):
        """Test Twitter connector capabilities."""
        from avatarfactory.connectors.twitter import TwitterConnector

        caps = TwitterConnector.get_capabilities()
        assert caps.platform == "twitter"
        assert caps.supports_topic_discovery is True
        assert caps.supports_persona_discovery is True
        assert caps.supports_publishing is True
        assert caps.supports_fetching is True
        assert len(caps.config_fields) >= 2

    def test_wecom_capabilities(self):
        """Test WeChat Work connector capabilities (send-only)."""
        from avatarfactory.connectors.wecom import WeComConnector

        caps = WeComConnector.get_capabilities()
        assert caps.platform == "wecom"
        assert caps.supports_topic_discovery is False
        assert caps.supports_persona_discovery is False
        assert caps.supports_publishing is True
        assert caps.supports_fetching is False

    def test_bing_search_capabilities(self):
        """Test Bing Search connector capabilities (read-only)."""
        from avatarfactory.connectors.bing_search import BingSearchConnector

        caps = BingSearchConnector.get_capabilities()
        assert caps.platform == "bing_search"
        assert caps.supports_topic_discovery is True
        assert caps.supports_persona_discovery is False
        assert caps.supports_publishing is False
        assert caps.supports_fetching is True

    def test_zhihu_capabilities(self):
        """Test Zhihu connector capabilities (fetch-only)."""
        from avatarfactory.connectors.zhihu import ZhihuConnector

        caps = ZhihuConnector.get_capabilities()
        assert caps.platform == "zhihu"
        assert caps.supports_topic_discovery is True
        assert caps.supports_persona_discovery is True
        assert caps.supports_publishing is False
        assert caps.supports_fetching is True

    def test_all_connectors_have_config_fields(self):
        """Test that all connectors define config fields."""
        all_caps = ConnectorRegistry.get_all_capabilities()
        for platform, caps in all_caps.items():
            assert len(caps.config_fields) > 0, (
                f"Connector '{platform}' has no config_fields defined"
            )

    def test_all_connectors_have_usage_guide(self):
        """Test that all connectors define a usage guide."""
        all_caps = ConnectorRegistry.get_all_capabilities()
        for platform, caps in all_caps.items():
            assert caps.usage_guide != "", (
                f"Connector '{platform}' has no usage_guide defined"
            )

    def test_required_fields_have_env_var(self):
        """Test that required config fields have env_var fallback."""
        all_caps = ConnectorRegistry.get_all_capabilities()
        for platform, caps in all_caps.items():
            for field in caps.config_fields:
                if field.required:
                    assert field.env_var is not None, (
                        f"Required field '{field.name}' in '{platform}' "
                        f"has no env_var fallback"
                    )


class TestRegistryCapabilityQueries:
    """Test ConnectorRegistry capability query methods."""

    def test_get_connector_capabilities(self):
        """Test getting capabilities for a specific platform."""
        caps = ConnectorRegistry.get_connector_capabilities("bluesky")
        assert caps is not None
        assert caps.platform == "bluesky"

    def test_get_connector_capabilities_alias(self):
        """Test getting capabilities via alias."""
        caps = ConnectorRegistry.get_connector_capabilities("bsky")
        assert caps is not None
        assert caps.platform == "bluesky"

    def test_get_connector_capabilities_unknown(self):
        """Test getting capabilities for unknown platform returns None."""
        caps = ConnectorRegistry.get_connector_capabilities("unknown_platform")
        assert caps is None

    def test_get_all_capabilities(self):
        """Test getting all connector capabilities."""
        all_caps = ConnectorRegistry.get_all_capabilities()
        assert isinstance(all_caps, dict)
        assert len(all_caps) >= 13  # At least 13 unique platforms
        assert "bluesky" in all_caps
        assert "twitter" in all_caps
        assert "wecom" in all_caps

    def test_get_all_capabilities_deduplicates_aliases(self):
        """Test that aliases don't create duplicate entries."""
        all_caps = ConnectorRegistry.get_all_capabilities()
        # "bsky" and "bluesky" should resolve to the same entry
        platforms = list(all_caps.keys())
        assert "bluesky" in platforms
        assert "bsky" not in platforms

    def test_list_topic_discovery_connectors(self):
        """Test listing connectors that support topic discovery."""
        topic_connectors = ConnectorRegistry.list_topic_discovery_connectors()
        assert isinstance(topic_connectors, list)
        assert "bluesky" in topic_connectors
        assert "twitter" in topic_connectors
        assert "bing_search" in topic_connectors
        # WeChat Work does NOT support topic discovery
        assert "wecom" not in topic_connectors

    def test_list_persona_discovery_connectors(self):
        """Test listing connectors that support persona discovery."""
        persona_connectors = ConnectorRegistry.list_persona_discovery_connectors()
        assert isinstance(persona_connectors, list)
        assert "bluesky" in persona_connectors
        assert "twitter" in persona_connectors
        assert "zhihu" in persona_connectors
        # Search connectors do NOT support persona discovery
        assert "bing_search" not in persona_connectors
        assert "brave_search" not in persona_connectors

    def test_topic_discovery_is_subset_of_fetching(self):
        """Test that topic discovery connectors all support fetching."""
        topic_connectors = ConnectorRegistry.list_topic_discovery_connectors()
        all_caps = ConnectorRegistry.get_all_capabilities()
        for platform in topic_connectors:
            assert all_caps[platform].supports_fetching is True, (
                f"Topic discovery connector '{platform}' does not support fetching"
            )

    def test_persona_discovery_is_subset_of_fetching(self):
        """Test that persona discovery connectors all support fetching."""
        persona_connectors = ConnectorRegistry.list_persona_discovery_connectors()
        all_caps = ConnectorRegistry.get_all_capabilities()
        for platform in persona_connectors:
            assert all_caps[platform].supports_fetching is True, (
                f"Persona discovery connector '{platform}' does not support fetching"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
