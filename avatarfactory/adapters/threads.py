"""
Threads platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class ThreadsAdapter(BasePlatformAdapter):
    """Meta Threads-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.THREADS)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Threads content guidelines"""
        return {
            "post_max_length": 500,
            "body_length": {"min": 1, "max": 500, "optimal": 200},
            "tone": "Conversational, authentic, relatable",
            "structure": "Hook → Thought → Reaction",
            "image_count": {"min": 0, "max": 1, "optimal": 1},
            "content_types": [
                "Conversational post",
                "Opinion/thought",
                "Question to community",
                "Quick tip",
                "Personal update",
            ],
            "engagement_tactics": [
                "Keep posts short and punchy",
                "Ask follow-up questions",
                "Reply to comments to boost visibility",
                "Cross-post with Instagram where relevant",
                "Share genuine opinions and experiences",
            ],
            "avoid": [
                "Long walls of text",
                "Excessive hashtag use",
                "Blatant promotional content",
                "Controversial inflammatory content",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Threads"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check post length
        post_length = len(content.body)
        if post_length > guidelines["post_max_length"]:
            issues.append(
                f"Post too long ({post_length} chars, max {guidelines['post_max_length']})"
            )

        # Check hashtag count (Threads is minimal on hashtags)
        hashtag_count = len(content.tags)
        if hashtag_count > 10:
            warnings.append("Consider fewer hashtags for Threads (hashtags are less prominent)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Threads export"""
        post_text = content.body.strip()

        # Truncate if needed (reserve 3 chars for "..." suffix to stay under 500 char limit)
        max_length = 500
        ellipsis = "..."
        if len(post_text) > max_length:
            post_text = post_text[: max_length - len(ellipsis)] + ellipsis

        # Add minimal hashtags
        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags[:3]])
            if len(post_text) + len(hashtags) + 2 <= 500:
                post_text = f"{post_text}\n\n{hashtags}"

        return {
            "platform": "threads",
            "text": post_text,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "post",
                "posting_tips": [
                    "Keep posts concise and conversational",
                    "Engage with replies to increase reach",
                    "Cross-promote between Instagram and Threads",
                    "Use authentic voice — Threads rewards genuine content",
                    "Post consistently to build following",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Threads"""
        return [
            "8:00-10:00",
            "12:00-14:00",
            "19:00-21:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Threads hashtag strategy"""
        return {
            "recommended_count": 1,
            "max_count": 3,
            "placement": "end_of_post",
            "guidelines": [
                "Use minimal hashtags (1-3 max)",
                "Focus on high-relevance tags only",
                "Hashtags are less impactful on Threads than Instagram",
                "Consider skipping hashtags for a more authentic feel",
                "Use hashtags to join specific topic conversations",
            ],
        }
