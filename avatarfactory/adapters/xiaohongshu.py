"""
Xiaohongshu (小红书) platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class XiaohongshuAdapter(BasePlatformAdapter):
    """Xiaohongshu-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.XIAOHONGSHU)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Xiaohongshu content guidelines"""
        return {
            "title_style": "Catchy, emoji-rich, curiosity-driven",
            "body_length": {"min": 200, "max": 1000, "optimal": 500},
            "tone": "Friendly, personal, authentic",
            "structure": "Short paragraphs, lists, emojis between sections",
            "formatting": {
                "use_emojis": True,
                "emoji_frequency": "Every 1-2 sentences",
                "use_line_breaks": True,
                "use_lists": True,
            },
            "content_types": [
                "Product reviews",
                "Tutorials/How-to",
                "Personal experiences",
                "Recommendations/Lists",
                "Before/After comparisons",
            ],
            "engagement_hooks": [
                "Ask questions at the end",
                "Invite comments",
                "Use relatable scenarios",
                "Share personal stories",
            ],
            "avoid": [
                "Overly promotional language",
                "External links",
                "Sensitive political topics",
                "Unverified claims",
                "Copied content",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Xiaohongshu"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check body length
        body_length = len(content.body)
        if body_length < guidelines["body_length"]["min"]:
            issues.append(
                f"Content too short ({body_length} chars, min {guidelines['body_length']['min']})"
            )
        elif body_length > guidelines["body_length"]["max"]:
            warnings.append(
                f"Content may be too long for XHS ({body_length} chars, optimal {guidelines['body_length']['optimal']})"
            )

        # Check for emojis
        has_emoji = any(ord(char) > 0x1F300 for char in content.body)
        if not has_emoji:
            warnings.append("Consider adding emojis for better engagement on XHS")

        # Check title length
        if len(content.title) > 20:
            warnings.append("Title may be too long, consider shortening for mobile display")

        # Check for external links
        if "http://" in content.body or "https://" in content.body:
            issues.append("External links are not recommended on Xiaohongshu")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Xiaohongshu export"""
        # Add emoji to title if not present
        formatted_title = content.title
        if not any(ord(char) > 0x1F300 for char in formatted_title):
            formatted_title = f"✨ {formatted_title}"

        # Format body with proper line breaks
        formatted_body = content.body.strip()

        return {
            "platform": "xiaohongshu",
            "title": formatted_title,
            "content": formatted_body,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "note",
                "posting_tips": [
                    "Add 3-6 high-quality images",
                    "Use relevant topic tags",
                    "Post during peak hours (12:00-14:00, 20:00-22:00)",
                    "Respond to comments within first hour",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Xiaohongshu"""
        return [
            "7:00-9:00",
            "12:00-14:00",
            "18:00-20:00",
            "21:00-23:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Xiaohongshu hashtag strategy"""
        return {
            "recommended_count": 5,
            "max_count": 10,
            "placement": "end_of_content",
            "guidelines": [
                "Mix popular and niche tags",
                "Use brand-specific tags when relevant",
                "Include location tags if applicable",
                "Add trending topic tags",
            ],
        }
