"""
Weibo platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class WeiboAdapter(BasePlatformAdapter):
    """Weibo-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.WEIBO)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Weibo content guidelines"""
        return {
            "post_max_length": 2000,
            "body_length": {"min": 50, "max": 2000, "optimal": 500},
            "tone": "Lively, engaging, relatable, trending-aware",
            "structure": "Hook → Content → Interaction",
            "image_count": {"min": 0, "max": 9, "optimal": 3},
            "content_types": [
                "Hot topic commentary",
                "Personal insight",
                "Product/experience sharing",
                "Interactive question",
                "Industry news",
                "Funny/entertainment content",
            ],
            "engagement_tactics": [
                "Leverage trending topics (#话题#)",
                "Ask questions to drive comments",
                "Use @mentions for relevant accounts",
                "Post during peak hours",
                "Respond to comments to boost engagement",
            ],
            "avoid": [
                "Politically sensitive content",
                "Rumor spreading",
                "Copyright infringement",
                "Excessive commercial promotion without disclosure",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Weibo"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check post length
        post_length = len(content.body)
        if post_length > guidelines["post_max_length"]:
            issues.append(
                f"Post too long ({post_length} chars, max {guidelines['post_max_length']})"
            )

        # Check hashtag count
        hashtag_count = len(content.tags)
        if hashtag_count > 10:
            warnings.append("Too many hashtags for Weibo (max 10 recommended)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Weibo export"""
        post_text = content.body.strip()

        # Add Weibo-style hashtags (#tag# format)
        if content.tags:
            hashtags = " ".join([f"#{tag}#" for tag in content.tags[:10]])
            post_text = f"{post_text} {hashtags}"

        return {
            "platform": "weibo",
            "text": post_text,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "microblog",
                "posting_tips": [
                    "Post during peak hours (12:00-14:00, 21:00-23:00)",
                    "Use trending topic tags to increase visibility",
                    "Add 3-9 images for higher engagement",
                    "Respond to early comments to boost ranking",
                    "Leverage hot search topics when relevant",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Weibo"""
        return [
            "7:00-9:00",
            "12:00-14:00",
            "21:00-23:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Weibo hashtag strategy"""
        return {
            "recommended_count": 3,
            "max_count": 10,
            "placement": "end_of_post",
            "format": "#tag#",
            "guidelines": [
                "Use #话题# format for Weibo topics",
                "Check and use trending topics when relevant",
                "Create specific campaign hashtags",
                "Use 2-5 hashtags for best results",
                "Mix hot and niche topics",
            ],
        }
