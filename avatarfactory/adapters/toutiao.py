"""
Toutiao platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class ToutiaoAdapter(BasePlatformAdapter):
    """Toutiao-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.TOUTIAO)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Toutiao content guidelines"""
        return {
            "title_max_length": 30,
            "title_style": "Direct, value-forward, curiosity-driving",
            "body_length": {"min": 200, "max": 10000, "optimal": 1000},
            "tone": "Informative, accessible, news-like",
            "structure": "Title → Lead → Body → Summary",
            "image_count": {"min": 1, "max": 9, "optimal": 3},
            "content_types": [
                "News-style article",
                "How-to guide",
                "Opinion piece",
                "Microblog post (short form)",
                "Video content",
            ],
            "engagement_tactics": [
                "Use strong, clickable titles",
                "Add relevant images or cover image",
                "Use popular topic tags",
                "Write comprehensive, authoritative content",
                "Post regularly to build follower base",
            ],
            "avoid": [
                "Misleading clickbait titles",
                "Low-quality or plagiarized content",
                "Politically sensitive topics",
                "Exaggerated claims",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Toutiao"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check title length
        title_max = guidelines["title_max_length"]
        if content.title and len(content.title) > title_max:
            issues.append(f"Title too long ({len(content.title)} chars, max {title_max})")

        # Check body length
        body_length = len(content.body)
        if body_length < guidelines["body_length"]["min"]:
            warnings.append(
                f"Content may be too short for Toutiao ({body_length} chars, recommended min {guidelines['body_length']['min']})"
            )

        # Check hashtag count
        hashtag_count = len(content.tags)
        if hashtag_count > 5:
            warnings.append("Too many hashtags for Toutiao (max 5 recommended)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Toutiao export"""
        body_text = content.body.strip()

        # Add Weibo-style hashtags (#tag# format) at the end
        if content.tags:
            hashtags = " ".join([f"#{tag}#" for tag in content.tags[:5]])
            body_text = f"{body_text} {hashtags}"

        return {
            "platform": "toutiao",
            "title": content.title[:30] if content.title else "",
            "content": body_text,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "article" if len(content.body) > 500 else "microblog",
                "posting_tips": [
                    "Add a compelling cover image",
                    "Use trending topic tags for more reach",
                    "Post during peak hours (7:00-9:00, 12:00-14:00, 20:00-22:00)",
                    "Write a clear, engaging title under 30 characters",
                    "Consistent posting schedule builds follower trust",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Toutiao"""
        return [
            "7:00-9:00",
            "12:00-14:00",
            "20:00-22:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Toutiao hashtag strategy"""
        return {
            "recommended_count": 3,
            "max_count": 5,
            "placement": "end_of_content",
            "format": "#tag#",
            "guidelines": [
                "Use #话题# format for Toutiao topics",
                "Research trending topics in your niche",
                "Include category-specific tags for distribution",
                "Use 2-5 tags maximum",
                "Align tags with content for algorithm matching",
            ],
        }
