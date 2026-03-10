"""
Bluesky platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class BlueskyAdapter(BasePlatformAdapter):
    """Bluesky-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.BLUESKY)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Bluesky content guidelines"""
        return {
            "format": "thread",
            "max_length_per_post": 300,
            "thread_length": {"min": 1, "max": 20, "optimal": 5},
            "tone": "Conversational, authentic, community-focused",
            "structure": "Hook → Value → Engagement",
            "content_types": [
                "Thread (multi-post story/tutorial)",
                "Short opinion/observation",
                "Link share with commentary",
                "Question to community",
                "Announcement",
            ],
            "engagement_tactics": [
                "Start with a strong hook in the first post",
                "Use threads for longer content",
                "Engage with replies promptly",
                "Use relevant hashtags (2-5)",
                "Tag relevant people when appropriate",
            ],
            "avoid": [
                "Walls of text in a single post",
                "Excessive self-promotion",
                "Spam or repetitive content",
                "Misleading information",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Bluesky"""
        issues = []
        warnings = []

        # Check if content needs to be split into thread
        total_length = len(content.body)
        max_per_post = 300

        if total_length > max_per_post * 20:
            warnings.append(
                f"Content very long ({total_length} chars), will require many thread posts"
            )

        # Check hashtag count
        hashtag_count = len(content.tags)
        if hashtag_count > 10:
            warnings.append("Too many hashtags for Bluesky (max 10 recommended)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Bluesky thread"""
        posts = self._split_into_posts(content.body)

        if len(posts) > 1:
            numbered_posts = [f"{i+1}/{len(posts)} 🧵\n{post}" for i, post in enumerate(posts[:-1])]
            numbered_posts.append(f"{len(posts)}/{len(posts)}\n{posts[-1]}")
        else:
            numbered_posts = posts

        # Add hashtags to last post
        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags[:5]])
            if len(numbered_posts[-1]) + len(hashtags) + 2 <= 300:
                numbered_posts[-1] = f"{numbered_posts[-1]}\n\n{hashtags}"

        return {
            "platform": "bluesky",
            "posts": numbered_posts,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "post_count": len(numbered_posts),
                "posting_tips": [
                    "Post during peak hours for your audience",
                    "Engage with replies quickly",
                    "Use rich text features (bold, italic, links)",
                    "Add images to increase engagement",
                ],
            },
        }

    def _split_into_posts(self, text: str, max_length: int = 280) -> list[str]:
        """Split text into Bluesky-sized posts.

        Uses 280 (not 300) to leave room for thread numbering overhead (e.g., "1/5 🧵\\n").
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
        """Get best posting times for Bluesky"""
        return [
            "9:00-11:00",
            "12:00-14:00",
            "17:00-19:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Bluesky hashtag strategy"""
        return {
            "recommended_count": 3,
            "max_count": 5,
            "placement": "end_of_last_post",
            "guidelines": [
                "Use 2-5 relevant hashtags",
                "Mix popular and niche tags",
                "Create a branded hashtag for series",
                "Add hashtags to the last post in a thread",
            ],
        }
