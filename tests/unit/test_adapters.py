"""
Unit tests for platform adapters.
"""

import pytest

from avatarfactory.adapters import get_adapter
from avatarfactory.adapters.xiaohongshu import XiaohongshuAdapter
from avatarfactory.adapters.zhihu import ZhihuAdapter
from avatarfactory.adapters.twitter import TwitterAdapter
from avatarfactory.models.schemas import Content, PlatformType


@pytest.fixture
def sample_content():
    """Create sample content for testing"""
    return Content(
        id="test_content_001",
        persona_id="test_persona_001",
        title="How to Use Notion for Project Management",
        body="Notion is a powerful productivity tool that combines notes, tasks, databases, and more into one workspace. In this guide, we'll explore how to use Notion effectively for project management...",
        pillar="Productivity Tools",
        platform=PlatformType.XIAOHONGSHU,
        tags=["notion", "productivity", "project-management"],
    )


class TestAdapterFactory:
    """Test adapter factory function"""

    def test_get_xiaohongshu_adapter(self):
        """Test getting Xiaohongshu adapter"""
        adapter = get_adapter(PlatformType.XIAOHONGSHU)
        assert isinstance(adapter, XiaohongshuAdapter)
        assert adapter.platform == PlatformType.XIAOHONGSHU

    def test_get_zhihu_adapter(self):
        """Test getting Zhihu adapter"""
        adapter = get_adapter(PlatformType.ZHIHU)
        assert isinstance(adapter, ZhihuAdapter)
        assert adapter.platform == PlatformType.ZHIHU

    def test_get_twitter_adapter(self):
        """Test getting Twitter adapter"""
        adapter = get_adapter(PlatformType.TWITTER)
        assert isinstance(adapter, TwitterAdapter)
        assert adapter.platform == PlatformType.TWITTER


class TestXiaohongshuAdapter:
    """Test Xiaohongshu adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = XiaohongshuAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "title_max_length" in guidelines
        assert guidelines["title_max_length"] == 60
        assert "emoji_density" in guidelines
        assert "image_count" in guidelines

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = XiaohongshuAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True
        assert len(validation["issues"]) == 0

    def test_validate_content_title_too_long(self, sample_content):
        """Test validation fails for too-long title"""
        adapter = XiaohongshuAdapter()
        sample_content.title = "A" * 100  # Too long

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False
        assert len(validation["issues"]) > 0
        assert any("Title too long" in issue for issue in validation["issues"])

    def test_validate_content_external_links(self, sample_content):
        """Test validation fails for external links"""
        adapter = XiaohongshuAdapter()
        sample_content.body = "Check out https://example.com for more info"

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False
        assert any("External links" in issue for issue in validation["issues"])

    def test_format_for_export(self, sample_content):
        """Test formatting content for export"""
        adapter = XiaohongshuAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "xiaohongshu"
        assert "title" in formatted
        assert "content" in formatted
        assert "metadata" in formatted
        assert formatted["metadata"]["suggested_image_count"] == 6

    def test_get_best_posting_times(self):
        """Test getting best posting times"""
        adapter = XiaohongshuAdapter()
        times = adapter.get_best_posting_times()

        assert len(times) > 0
        assert any("9" in time or "10" in time for time in times)  # Morning peak

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = XiaohongshuAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert "recommended_count" in strategy
        assert strategy["recommended_count"] == 5
        assert "guidelines" in strategy


class TestZhihuAdapter:
    """Test Zhihu adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = ZhihuAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "body_length" in guidelines
        assert guidelines["body_length"]["min"] == 500  # Long-form content
        assert guidelines["tone"] == "Professional, in-depth, analytical"

    def test_validate_content_too_short(self, sample_content):
        """Test validation warns for short content"""
        adapter = ZhihuAdapter()
        sample_content.body = "Short content"  # Too short for Zhihu

        validation = adapter.validate_content(sample_content)

        assert len(validation["warnings"]) > 0
        assert any("too short" in warning.lower() for warning in validation["warnings"])

    def test_format_for_export(self, sample_content):
        """Test formatting content for export"""
        adapter = ZhihuAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "zhihu"
        assert formatted["metadata"]["content_type"] == "article"


class TestTwitterAdapter:
    """Test Twitter adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = TwitterAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "max_length_per_tweet" in guidelines
        assert guidelines["max_length_per_tweet"] == 280
        assert guidelines["format"] == "thread"

    def test_split_into_tweets_short_content(self):
        """Test splitting short content into tweets"""
        adapter = TwitterAdapter()
        short_text = "This is a short tweet that fits in one tweet."

        tweets = adapter._split_into_tweets(short_text)

        assert len(tweets) == 1
        assert tweets[0] == short_text

    def test_split_into_tweets_long_content(self):
        """Test splitting long content into multiple tweets"""
        adapter = TwitterAdapter()
        long_text = "\n\n".join([f"This is paragraph {i}. " * 20 for i in range(5)])

        tweets = adapter._split_into_tweets(long_text)

        assert len(tweets) > 1
        for tweet in tweets:
            assert len(tweet) <= 250  # Default max_length in _split_into_tweets

    def test_format_for_export(self, sample_content):
        """Test formatting content for export as thread"""
        adapter = TwitterAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "twitter"
        assert "thread" in formatted
        assert isinstance(formatted["thread"], list)
        assert formatted["metadata"]["tweet_count"] > 0

    def test_format_adds_numbering(self, sample_content):
        """Test that thread tweets are numbered"""
        adapter = TwitterAdapter()
        # Make content long enough for multiple tweets
        sample_content.body = "\n\n".join([f"Paragraph {i}. " * 30 for i in range(3)])

        formatted = adapter.format_for_export(sample_content)
        thread = formatted["thread"]

        if len(thread) > 1:
            # Check first tweet has numbering
            assert thread[0].startswith("1/")

    def test_hashtag_strategy(self):
        """Test Twitter hashtag strategy"""
        adapter = TwitterAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy["recommended_count"] == 1
        assert strategy["max_count"] == 2  # Twitter uses fewer hashtags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
