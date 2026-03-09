"""
Unit tests for platform adapters.
"""

import pytest

from avatarfactory.adapters import get_adapter
from avatarfactory.adapters.bluesky import BlueskyAdapter
from avatarfactory.adapters.instagram import InstagramAdapter
from avatarfactory.adapters.linkedin import LinkedInAdapter
from avatarfactory.adapters.mastodon import MastodonAdapter
from avatarfactory.adapters.threads import ThreadsAdapter
from avatarfactory.adapters.toutiao import ToutiaoAdapter
from avatarfactory.adapters.twitter import TwitterAdapter
from avatarfactory.adapters.weibo import WeiboAdapter
from avatarfactory.adapters.xiaohongshu import XiaohongshuAdapter
from avatarfactory.adapters.zhihu import ZhihuAdapter
from avatarfactory.models.schemas import Content, PlatformType


@pytest.fixture
def sample_content():
    """Create sample content for testing"""
    return Content(
        id="test_content_001",
        persona_id="test_persona_001",
        title="How to Use Notion for PM",
        body="Notion is a powerful productivity tool that combines notes, tasks, databases, and more into one workspace. In this guide, we'll explore how to use Notion effectively for project management. Here are some tips to get started with Notion today!",
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

    def test_get_bluesky_adapter(self):
        """Test getting Bluesky adapter"""
        adapter = get_adapter(PlatformType.BLUESKY)
        assert isinstance(adapter, BlueskyAdapter)
        assert adapter.platform == PlatformType.BLUESKY

    def test_get_instagram_adapter(self):
        """Test getting Instagram adapter"""
        adapter = get_adapter(PlatformType.INSTAGRAM)
        assert isinstance(adapter, InstagramAdapter)
        assert adapter.platform == PlatformType.INSTAGRAM

    def test_get_linkedin_adapter(self):
        """Test getting LinkedIn adapter"""
        adapter = get_adapter(PlatformType.LINKEDIN)
        assert isinstance(adapter, LinkedInAdapter)
        assert adapter.platform == PlatformType.LINKEDIN

    def test_get_mastodon_adapter(self):
        """Test getting Mastodon adapter"""
        adapter = get_adapter(PlatformType.MASTODON)
        assert isinstance(adapter, MastodonAdapter)
        assert adapter.platform == PlatformType.MASTODON

    def test_get_threads_adapter(self):
        """Test getting Threads adapter"""
        adapter = get_adapter(PlatformType.THREADS)
        assert isinstance(adapter, ThreadsAdapter)
        assert adapter.platform == PlatformType.THREADS

    def test_get_toutiao_adapter(self):
        """Test getting Toutiao adapter"""
        adapter = get_adapter(PlatformType.TOUTIAO)
        assert isinstance(adapter, ToutiaoAdapter)
        assert adapter.platform == PlatformType.TOUTIAO

    def test_get_weibo_adapter(self):
        """Test getting Weibo adapter"""
        adapter = get_adapter(PlatformType.WEIBO)
        assert isinstance(adapter, WeiboAdapter)
        assert adapter.platform == PlatformType.WEIBO

    def test_unknown_platform_raises(self):
        """Test that unknown platform raises ValueError"""
        with pytest.raises(ValueError, match="No adapter available"):
            get_adapter("unknown_platform")


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


class TestBlueskyAdapter:
    """Test Bluesky adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = BlueskyAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "max_length_per_post" in guidelines
        assert guidelines["max_length_per_post"] == 300
        assert guidelines["format"] == "thread"

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = BlueskyAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True
        assert len(validation["issues"]) == 0

    def test_format_for_export_single(self, sample_content):
        """Test formatting short content as single post"""
        adapter = BlueskyAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "bluesky"
        assert "posts" in formatted
        assert isinstance(formatted["posts"], list)
        assert formatted["metadata"]["post_count"] > 0

    def test_format_for_export_thread(self, sample_content):
        """Test formatting long content as thread"""
        adapter = BlueskyAdapter()
        sample_content.body = " ".join(["word"] * 400)  # Very long content

        formatted = adapter.format_for_export(sample_content)

        assert len(formatted["posts"]) > 1
        # Check numbering on first post
        assert formatted["posts"][0].startswith("1/")

    def test_get_best_posting_times(self):
        """Test getting best posting times"""
        adapter = BlueskyAdapter()
        times = adapter.get_best_posting_times()

        assert len(times) > 0

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = BlueskyAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert "recommended_count" in strategy
        assert strategy["recommended_count"] == 3


class TestInstagramAdapter:
    """Test Instagram adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = InstagramAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "caption_max_length" in guidelines
        assert guidelines["caption_max_length"] == 2200

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = InstagramAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True

    def test_validate_content_too_long(self, sample_content):
        """Test validation fails for caption too long"""
        adapter = InstagramAdapter()
        sample_content.body = "A" * 2300  # Over 2200 char limit

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False
        assert any("too long" in issue.lower() for issue in validation["issues"])

    def test_format_for_export(self, sample_content):
        """Test formatting content for Instagram"""
        adapter = InstagramAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "instagram"
        assert "caption" in formatted
        assert "metadata" in formatted

    def test_hashtag_format(self, sample_content):
        """Test hashtags are added to caption"""
        adapter = InstagramAdapter()
        formatted = adapter.format_for_export(sample_content)

        for tag in sample_content.tags:
            assert f"#{tag}" in formatted["caption"]

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = InstagramAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy["recommended_count"] == 20
        assert strategy["max_count"] == 30


class TestLinkedInAdapter:
    """Test LinkedIn adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = LinkedInAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "post_max_length" in guidelines
        assert guidelines["post_max_length"] == 3000

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = LinkedInAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True

    def test_validate_content_too_long(self, sample_content):
        """Test validation fails for post too long"""
        adapter = LinkedInAdapter()
        sample_content.body = "A" * 3100  # Over 3000 char limit

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False
        assert any("too long" in issue.lower() for issue in validation["issues"])

    def test_format_for_export(self, sample_content):
        """Test formatting content for LinkedIn"""
        adapter = LinkedInAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "linkedin"
        assert "text" in formatted
        assert "metadata" in formatted

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = LinkedInAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy["recommended_count"] == 3
        assert strategy["max_count"] == 5


class TestMastodonAdapter:
    """Test Mastodon adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = MastodonAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "max_length_per_post" in guidelines
        assert guidelines["max_length_per_post"] == 500

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = MastodonAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True

    def test_format_for_export_single(self, sample_content):
        """Test formatting short content as single post"""
        adapter = MastodonAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "mastodon"
        assert "posts" in formatted

    def test_format_for_export_thread(self, sample_content):
        """Test formatting long content as thread"""
        adapter = MastodonAdapter()
        sample_content.body = " ".join(["word"] * 600)  # Very long content

        formatted = adapter.format_for_export(sample_content)

        assert len(formatted["posts"]) > 1

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = MastodonAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy["recommended_count"] == 5


class TestWeiboAdapter:
    """Test Weibo adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = WeiboAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "post_max_length" in guidelines
        assert guidelines["post_max_length"] == 2000

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = WeiboAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True

    def test_validate_content_too_long(self, sample_content):
        """Test validation fails for post too long"""
        adapter = WeiboAdapter()
        sample_content.body = "A" * 2100  # Over 2000 char limit

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False

    def test_format_for_export_weibo_hashtags(self, sample_content):
        """Test Weibo uses #tag# format"""
        adapter = WeiboAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "weibo"
        # Weibo uses #tag# format
        for tag in sample_content.tags:
            assert f"#{tag}#" in formatted["text"]

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = WeiboAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy.get("format") == "#tag#"


class TestToutiaoAdapter:
    """Test Toutiao adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = ToutiaoAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "title_max_length" in guidelines
        assert guidelines["title_max_length"] == 30

    def test_validate_content_title_too_long(self, sample_content):
        """Test validation fails for title too long"""
        adapter = ToutiaoAdapter()
        sample_content.title = "A" * 35  # Over 30 char limit

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False
        assert any("Title too long" in issue for issue in validation["issues"])

    def test_format_for_export(self, sample_content):
        """Test formatting content for Toutiao"""
        adapter = ToutiaoAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "toutiao"
        assert "title" in formatted
        assert "content" in formatted
        assert len(formatted["title"]) <= 30  # Title truncated to 30 chars

    def test_format_detects_article_vs_microblog(self, sample_content):
        """Test that format detects article vs microblog based on content length"""
        adapter = ToutiaoAdapter()

        # Short content -> microblog
        sample_content.body = "Short content."
        formatted = adapter.format_for_export(sample_content)
        assert formatted["metadata"]["content_type"] == "microblog"

        # Long content -> article
        sample_content.body = "Long content. " * 50
        formatted = adapter.format_for_export(sample_content)
        assert formatted["metadata"]["content_type"] == "article"

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = ToutiaoAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy["max_count"] == 5


class TestThreadsAdapter:
    """Test Threads adapter"""

    def test_get_content_guidelines(self):
        """Test getting content guidelines"""
        adapter = ThreadsAdapter()
        guidelines = adapter.get_content_guidelines()

        assert "post_max_length" in guidelines
        assert guidelines["post_max_length"] == 500

    def test_validate_content_valid(self, sample_content):
        """Test validating valid content"""
        adapter = ThreadsAdapter()
        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is True

    def test_validate_content_too_long(self, sample_content):
        """Test validation fails for post too long"""
        adapter = ThreadsAdapter()
        sample_content.body = "A" * 600  # Over 500 char limit

        validation = adapter.validate_content(sample_content)

        assert validation["valid"] is False

    def test_format_for_export(self, sample_content):
        """Test formatting content for Threads"""
        adapter = ThreadsAdapter()
        formatted = adapter.format_for_export(sample_content)

        assert formatted["platform"] == "threads"
        assert "text" in formatted
        assert len(formatted["text"]) <= 500  # Never exceeds limit

    def test_format_truncates_long_content(self, sample_content):
        """Test that overly long content is truncated"""
        adapter = ThreadsAdapter()
        sample_content.body = "A" * 600

        formatted = adapter.format_for_export(sample_content)

        assert len(formatted["text"]) <= 500
        assert formatted["text"].endswith("...")

    def test_get_hashtag_strategy(self):
        """Test getting hashtag strategy"""
        adapter = ThreadsAdapter()
        strategy = adapter.get_hashtag_strategy()

        assert strategy["recommended_count"] == 1
        assert strategy["max_count"] == 3


class TestPlatformTypeEnum:
    """Test PlatformType enum completeness"""

    def test_all_new_platforms_exist(self):
        """Test that all new platform types are defined"""
        assert PlatformType.BLUESKY == "bluesky"
        assert PlatformType.MASTODON == "mastodon"
        assert PlatformType.INSTAGRAM == "instagram"
        assert PlatformType.WEIBO == "weibo"
        assert PlatformType.LINKEDIN == "linkedin"
        assert PlatformType.THREADS == "threads"
        assert PlatformType.TOUTIAO == "toutiao"

    def test_original_platforms_still_exist(self):
        """Test that original platform types still exist"""
        assert PlatformType.XIAOHONGSHU == "xiaohongshu"
        assert PlatformType.ZHIHU == "zhihu"
        assert PlatformType.TWITTER == "twitter"
        assert PlatformType.DOUYIN == "douyin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
