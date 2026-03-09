"""
Mastodon platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class MastodonAdapter(BasePlatformAdapter):
    """Mastodon-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.MASTODON)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Mastodon content guidelines"""
        return {
            "format": "thread",
            "max_length_per_post": 500,
            "thread_length": {"min": 1, "max": 20, "optimal": 5},
            "tone": "Conversational, authentic, community-oriented",
            "structure": "Idea → Context → Discussion",
            "content_types": [
                "Short status update",
                "Thread (multi-toot story)",
                "Link share with commentary",
                "Community question",
                "Announcement",
            ],
            "engagement_tactics": [
                "Use content warnings (CW) for sensitive topics",
                "Engage with local and federated timelines",
                "Use relevant hashtags for discovery",
                "Boost (reblog) community content",
                "Reply thoughtfully to build community",
            ],
            "avoid": [
                "Content without proper CW when needed",
                "Cross-posting identical content from other platforms",
                "Spam or unsolicited promotions",
                "Hate speech or harassment",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Mastodon"""
        issues = []
        warnings = []

        # Check if content needs to be split into thread
        total_length = len(content.body)
        max_per_post = 500

        if total_length > max_per_post * 20:
            warnings.append(
                f"Content very long ({total_length} chars), will require many thread posts"
            )

        # Check hashtag count
        hashtag_count = len(content.tags)
        if hashtag_count > 10:
            warnings.append("Consider limiting hashtags to 5-10 for Mastodon")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Mastodon thread"""
        posts = self._split_into_posts(content.body)

        if len(posts) > 1:
            numbered_posts = [f"{i+1}/{len(posts)} 🧵\n{post}" for i, post in enumerate(posts[:-1])]
            numbered_posts.append(f"{len(posts)}/{len(posts)}\n{posts[-1]}")
        else:
            numbered_posts = posts

        # Add hashtags to last post
        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags[:10]])
            if len(numbered_posts[-1]) + len(hashtags) + 2 <= 500:
                numbered_posts[-1] = f"{numbered_posts[-1]}\n\n{hashtags}"

        return {
            "platform": "mastodon",
            "posts": numbered_posts,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "post_count": len(numbered_posts),
                "posting_tips": [
                    "Add a content warning (CW) for sensitive topics",
                    "Choose appropriate visibility (public/unlisted/followers)",
                    "Engage with your home instance community",
                    "Use descriptive alt text for images",
                ],
            },
        }

    def _split_into_posts(self, text: str, max_length: int = 480) -> list[str]:
        """Split text into Mastodon-sized posts.

        Uses 480 (not 500) to leave room for thread numbering overhead (e.g., "1/5 🧵\\n").
        """
        posts = []
        paragraphs = text.split("\n\n")

        current_post = ""
        for para in paragraphs:
            if len(para) > max_length:
                if current_post:
                    posts.append(current_post.strip())
                    current_post = ""
                words = para.split()
                chunk = ""
                for word in words:
                    if len(chunk) + len(word) + 1 <= max_length:
                        chunk += (" " + word) if chunk else word
                    else:
                        if chunk:
                            posts.append(chunk.strip())
                        chunk = word
                if chunk:
                    current_post = chunk
            elif len(current_post) + len(para) + 2 <= max_length:
                current_post += (para + "\n\n") if current_post else para
            else:
                if current_post:
                    posts.append(current_post.strip())
                current_post = para

        if current_post:
            posts.append(current_post.strip())

        return posts

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Mastodon"""
        return [
            "9:00-11:00",
            "12:00-14:00",
            "18:00-20:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Mastodon hashtag strategy"""
        return {
            "recommended_count": 5,
            "max_count": 10,
            "placement": "end_of_last_post",
            "guidelines": [
                "Use CamelCase hashtags for screen reader accessibility",
                "Use topic-specific hashtags for federated discovery",
                "Avoid hashtag stuffing",
                "Use #introduction for new account posts",
                "Check local instance hashtag culture",
            ],
        }
