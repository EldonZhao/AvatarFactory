"""
Platform adapters for AvatarFactory.

Adapters provide platform-specific guidelines, validation, and formatting.
"""

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.adapters.xiaohongshu import XiaohongshuAdapter
from avatarfactory.adapters.zhihu import ZhihuAdapter
from avatarfactory.adapters.twitter import TwitterAdapter
from avatarfactory.models.schemas import PlatformType

__all__ = [
    "BasePlatformAdapter",
    "XiaohongshuAdapter",
    "ZhihuAdapter",
    "TwitterAdapter",
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
        PlatformType.XIAOHONGSHU: XiaohongshuAdapter,
        PlatformType.ZHIHU: ZhihuAdapter,
        PlatformType.TWITTER: TwitterAdapter,
    }

    adapter_class = adapters.get(platform)
    if not adapter_class:
        raise ValueError(f"No adapter available for platform: {platform}")

    return adapter_class()
