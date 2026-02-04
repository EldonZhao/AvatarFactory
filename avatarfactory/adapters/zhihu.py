"""
Zhihu (知乎) platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class ZhihuAdapter(BasePlatformAdapter):
    """Zhihu-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.ZHIHU)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Zhihu content guidelines"""
        return {
            "title_style": "Question-based or professional statement",
            "body_length": {"min": 500, "max": 5000, "optimal": 1500},
            "tone": "Professional, in-depth, analytical",
            "structure": "Logical flow, data-driven, long-form",
            "formatting": {
                "use_headings": True,
                "use_bullets": True,
                "use_quotes": True,
                "use_code_blocks": True,
            },
            "content_types": [
                "In-depth analysis",
                "Technical explanation",
                "Industry insights",
                "Research-backed arguments",
                "Personal expertise sharing",
            ],
            "credibility_signals": [
                "Cite sources and data",
                "Share professional experience",
                "Use proper terminology",
                "Acknowledge limitations",
                "Engage with comments professionally",
            ],
            "avoid": [
                "Shallow clickbait",
                "Unsupported claims",
                "Overly promotional content",
                "Low-effort responses",
                "Emotional/aggressive tone",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Zhihu"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check body length
        body_length = len(content.body)
        if body_length < guidelines["body_length"]["min"]:
            warnings.append(
                f"Content too short for Zhihu ({body_length} chars, min {guidelines['body_length']['min']})"
            )

        # Check for depth indicators
        has_headings = any(line.startswith("#") for line in content.body.split("\n"))
        if not has_headings and body_length > 800:
            warnings.append("Consider adding section headings for better structure")

        # Check for data/evidence
        has_numbers = any(char.isdigit() for char in content.body)
        if not has_numbers:
            warnings.append("Consider adding data or statistics for credibility")

        # Check for proper formatting
        if "**" not in content.body and "__" not in content.body:
            warnings.append("Consider using bold for emphasis on key points")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Zhihu export"""
        formatted_title = content.title.strip()
        formatted_body = content.body.strip()

        return {
            "platform": "zhihu",
            "title": formatted_title,
            "content": formatted_body,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "article",
                "posting_tips": [
                    "Add relevant images/charts to support arguments",
                    "Respond to comments to boost engagement",
                    "Update content with new information over time",
                    "Link to related answers you've written",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Zhihu"""
        return [
            "8:00-9:00",
            "12:00-14:00",
            "21:00-23:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Zhihu hashtag strategy"""
        return {
            "recommended_count": 3,
            "max_count": 5,
            "placement": "topics",
            "guidelines": [
                "Use specific topic tags",
                "Choose relevant professional fields",
                "Participate in trending discussions",
                "Build expertise in specific topics",
            ],
        }
