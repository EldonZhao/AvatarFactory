"""
LinkedIn platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class LinkedInAdapter(BasePlatformAdapter):
    """LinkedIn-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.LINKEDIN)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get LinkedIn content guidelines"""
        return {
            "post_max_length": 3000,
            "body_length": {"min": 100, "max": 3000, "optimal": 1000},
            "tone": "Professional, insightful, value-driven",
            "structure": "Hook → Insight → Takeaways → CTA",
            "content_types": [
                "Thought leadership article",
                "Industry insights",
                "Career advice",
                "Company updates",
                "How-to guides",
                "Professional achievements",
            ],
            "engagement_tactics": [
                "Start with a strong opening line",
                "Use short paragraphs and white space",
                "Share personal experiences and lessons",
                "Ask a question to spark discussion",
                "Tag relevant people and companies",
                "Use 3-5 relevant hashtags",
            ],
            "avoid": [
                "Overly casual language",
                "Controversial personal opinions",
                "Excessive promotional content",
                "Vague or generic advice",
                "Too many hashtags",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for LinkedIn"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check post length
        post_length = len(content.body)
        if post_length > guidelines["post_max_length"]:
            issues.append(
                f"Post too long ({post_length} chars, max {guidelines['post_max_length']})"
            )
        elif post_length < guidelines["body_length"]["min"]:
            warnings.append(
                f"Post too short for LinkedIn ({post_length} chars, recommended min {guidelines['body_length']['min']})"
            )

        # Check hashtag count (LinkedIn recommends 3-5)
        hashtag_count = len(content.tags)
        if hashtag_count > 10:
            warnings.append("Too many hashtags for LinkedIn (3-5 recommended)")
        elif hashtag_count == 0:
            warnings.append("Consider adding 3-5 relevant hashtags for discoverability")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for LinkedIn export"""
        post_text = content.body.strip()

        # Add hashtags at the end
        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags[:5]])
            post_text = f"{post_text}\n\n{hashtags}"

        return {
            "platform": "linkedin",
            "text": post_text,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "content_type": "post",
                "posting_tips": [
                    "Post during business hours (Tue-Thu, 8:00-10:00, 12:00-14:00)",
                    "Engage with comments to boost algorithm reach",
                    "Share to relevant LinkedIn groups",
                    "Consider adding a document/PDF for higher engagement",
                    "Tag company pages and colleagues when relevant",
                ],
            },
        }

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for LinkedIn"""
        return [
            "8:00-10:00",
            "12:00-14:00",
            "17:00-18:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get LinkedIn hashtag strategy"""
        return {
            "recommended_count": 3,
            "max_count": 5,
            "placement": "end_of_post",
            "guidelines": [
                "Use 3-5 highly relevant professional hashtags",
                "Mix industry-specific and broader professional tags",
                "Follow hashtags to see what your audience engages with",
                "Create a personal brand hashtag for your content series",
                "Avoid over-trending or irrelevant hashtags",
            ],
        }
