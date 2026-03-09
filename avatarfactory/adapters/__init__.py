"""
Platform adapters for AvatarFactory.

Adapters provide platform-specific guidelines, validation, and formatting.
"""

from avatarfactory.adapters.base import BasePlatformAdapter
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
from avatarfactory.models.schemas import PlatformType

__all__ = [
    "BasePlatformAdapter",
    "BlueskyAdapter",
    "InstagramAdapter",
    "LinkedInAdapter",
    "MastodonAdapter",
    "ThreadsAdapter",
    "ToutiaoAdapter",
    "TwitterAdapter",
    "WeiboAdapter",
    "XiaohongshuAdapter",
    "ZhihuAdapter",
    "get_adapter",
]


def get_adapter(platform: PlatformType) -> BasePlatformAdapter:
    """
    Get platform adapter instance.

    Args:
        platform: Platform type

    Returns:
        Platform adapter instance

    Example:
        adapter = get_adapter(PlatformType.XIAOHONGSHU)
        guidelines = adapter.get_content_guidelines()
    """
    adapters = {
        PlatformType.BLUESKY: BlueskyAdapter,
        PlatformType.INSTAGRAM: InstagramAdapter,
        PlatformType.LINKEDIN: LinkedInAdapter,
        PlatformType.MASTODON: MastodonAdapter,
        PlatformType.THREADS: ThreadsAdapter,
        PlatformType.TOUTIAO: ToutiaoAdapter,
        PlatformType.TWITTER: TwitterAdapter,
        PlatformType.WEIBO: WeiboAdapter,
        PlatformType.XIAOHONGSHU: XiaohongshuAdapter,
        PlatformType.ZHIHU: ZhihuAdapter,
    }

    adapter_class = adapters.get(platform)
    if not adapter_class:
        raise ValueError(f"No adapter available for platform: {platform}")

    return adapter_class()
