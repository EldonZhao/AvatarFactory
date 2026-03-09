"""
Instagram platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class InstagramAdapter(BasePlatformAdapter):
    """Instagram-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.INSTAGRAM)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Instagram content guidelines"""
        return {
            "caption_max_length": 2200,
            "caption_style": "Visual storytelling, authentic, aspirational",
            "body_length": {"min": 100, "max": 2200, "optimal": 500},
            "tone": "Visual, engaging, personal",
            "structure": "Hook → Story → CTA",
            "image_count": {"min": 1, "max": 10, "optimal": 1},
            "content_types": [
                "Single image post",
                "Carousel (up to 10 images)",
                "Reels (short video)",
                "Stories (ephemeral)",
                "Behind-the-scenes",
            ],
            "engagement_tactics": [
                "Use a strong visual hook",
                "Ask questions to drive comments",
                "Use up to 30 hashtags (in caption or first comment)",
                "Tag relevant accounts",
                "Include a CTA",
            ],
            "avoid": [
                "Too much text in image",
                "Poor quality images",
                "Irrelevant hashtags",
                "Fake engagement tactics",
                "External links in captions (not clickable)",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Instagram"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check caption length
        caption_length = len(content.body)
        if caption_length > guidelines["caption_max_length"]:
            issues.append(
                f"Caption too long ({caption_length} chars, max {guidelines['caption_max_length']})"
            )

        # Check hashtag count
        hashtag_count = len(content.tags)
        if hashtag_count > 30:
            warnings.append("Too many hashtags (max 30 on Instagram)")
        elif hashtag_count == 0:
            warnings.append("Consider adding hashtags to increase discoverability")

        # Instagram requires at least one image for feed posts
        if not content.media and not content.image_prompts:
            warnings.append("Instagram feed posts require at least one image")

        # Check for URLs in caption
        if "http://" in content.body or "https://" in content.body:
            warnings.append("URLs in Instagram captions are not clickable; use bio link instead")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Instagram export"""
        caption = content.body.strip()

        # Add hashtags at the end
        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags[:30]])
            caption = f"{caption}\n\n{hashtags}"

        return {
            "platform": "instagram",
            "caption": caption,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "feed_post",
                "posting_tips": [
                    "Use a high-quality image or video",
                    "Post during peak hours (11:00-13:00, 19:00-21:00)",
                    "Engage with comments within the first hour",
                    "Consider using carousel format for tutorials",
                    "Add location tag if relevant",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Instagram"""
        return [
            "6:00-9:00",
            "11:00-13:00",
            "19:00-21:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Instagram hashtag strategy"""
        return {
            "recommended_count": 20,
            "max_count": 30,
            "placement": "end_of_caption",
            "guidelines": [
                "Use a mix of popular (1M+), medium (100K-1M), and niche (<100K) hashtags",
                "Create a branded hashtag for your content series",
                "Research competitor hashtags",
                "Rotate hashtag sets to avoid shadowban",
                "Consider posting hashtags in first comment",
            ],
        }
