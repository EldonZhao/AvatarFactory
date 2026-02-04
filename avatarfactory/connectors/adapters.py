"""
Platform content adapters for AvatarFactory.

Handles content transformation and adaptation for different social platforms,
respecting each platform's content limits and formatting requirements.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from avatarfactory.models.schemas import Content


@dataclass
class PlatformLimits:
    """Content limits for a platform."""
    max_text_length: int  # Maximum text length per post
    max_title_length: int  # Maximum title length (0 if no title support)
    max_images: int  # Maximum images per post
    max_tags: int  # Maximum hashtags
    supports_threads: bool  # Can post multi-part threads
    supports_title: bool  # Has separate title field
    supports_markdown: bool  # Supports markdown formatting
    thread_connector: str = ""  # Text to connect thread parts (e.g., "🧵")


# Platform-specific limits
PLATFORM_LIMITS: Dict[str, PlatformLimits] = {
    "bluesky": PlatformLimits(
        max_text_length=300,
        max_title_length=0,
        max_images=4,
        max_tags=10,
        supports_threads=True,
        supports_title=False,
        supports_markdown=False,
        thread_connector="🧵",
    ),
    "twitter": PlatformLimits(
        max_text_length=280,
        max_title_length=0,
        max_images=4,
        max_tags=5,
        supports_threads=True,
        supports_title=False,
        supports_markdown=False,
        thread_connector="🧵",
    ),
    "xiaohongshu": PlatformLimits(
        max_text_length=1000,
        max_title_length=20,
        max_images=9,
        max_tags=10,
        supports_threads=False,
        supports_title=True,
        supports_markdown=False,
    ),
    "zhihu": PlatformLimits(
        max_text_length=100000,  # Very long form
        max_title_length=100,
        max_images=50,
        max_tags=5,
        supports_threads=False,
        supports_title=True,
        supports_markdown=True,
    ),
}


@dataclass
class AdaptedContent:
    """Content adapted for a specific platform."""
    platform: str
    parts: List[str]  # Content split into parts (for threads) or single part
    title: Optional[str]
    tags: List[str]
    images: List[str]
    is_thread: bool
    original_length: int
    adapted_length: int
    truncated: bool


class ContentAdapter:
    """Adapts content for different social platforms."""

    def __init__(self, platform: str):
        self.platform = platform.lower()
        self.limits = PLATFORM_LIMITS.get(self.platform)
        if not self.limits:
            # Default conservative limits
            self.limits = PlatformLimits(
                max_text_length=500,
                max_title_length=100,
                max_images=4,
                max_tags=10,
                supports_threads=False,
                supports_title=True,
                supports_markdown=False,
            )

    def adapt(
        self,
        content: Content,
        images: Optional[List[str]] = None,
        force_single: bool = False,
    ) -> AdaptedContent:
        """
        Adapt content for the target platform.

        Args:
            content: The Content object to adapt
            images: Optional list of image paths to include
            force_single: Force single post (truncate instead of thread)

        Returns:
            AdaptedContent with platform-appropriate formatting
        """
        # Get text content
        text = content.body
        title = content.title
        tags = content.tags[:self.limits.max_tags] if content.tags else []
        image_list = (images or [])[:self.limits.max_images]

        original_length = len(text)

        # For platforms without title support, use title as first post in thread
        if title and not self.limits.supports_title and self.limits.supports_threads:
            # Title becomes first post, body becomes replies
            body_parts = self._split_into_thread(text, tags)
            # Prepend title as first post (no thread indicator on title)
            title_post = f"📌 {title}"
            # Re-number the body parts starting from 2
            total = len(body_parts) + 1
            renumbered_parts = []
            for i, part in enumerate(body_parts):
                # Remove old numbering if present and add new
                import re
                part_text = re.sub(r'^\d+/\d+\s*🧵?\s*\n?', '', part)
                if i < len(body_parts) - 1:
                    renumbered_parts.append(f"{i+2}/{total} 🧵\n{part_text}")
                else:
                    renumbered_parts.append(f"{i+2}/{total}\n{part_text}")

            all_parts = [title_post] + renumbered_parts
            return AdaptedContent(
                platform=self.platform,
                parts=all_parts,
                title=None,  # Title is now in parts
                tags=tags,
                images=image_list,
                is_thread=True,
                original_length=original_length,
                adapted_length=sum(len(p) for p in all_parts),
                truncated=False,
            )

        # Check if content fits in single post
        if len(text) <= self.limits.max_text_length:
            return AdaptedContent(
                platform=self.platform,
                parts=[text],
                title=title,
                tags=tags,
                images=image_list,
                is_thread=False,
                original_length=original_length,
                adapted_length=len(text),
                truncated=False,
            )

        # Content is too long - need to split or truncate
        if self.limits.supports_threads and not force_single:
            # Split into thread
            parts = self._split_into_thread(text, tags)
            return AdaptedContent(
                platform=self.platform,
                parts=parts,
                title=title,
                tags=tags,
                images=image_list,
                is_thread=True,
                original_length=original_length,
                adapted_length=sum(len(p) for p in parts),
                truncated=False,
            )
        else:
            # Truncate to fit
            truncated_text = self._smart_truncate(text)
            return AdaptedContent(
                platform=self.platform,
                parts=[truncated_text],
                title=title,
                tags=tags,
                images=image_list,
                is_thread=False,
                original_length=original_length,
                adapted_length=len(truncated_text),
                truncated=True,
            )

    def adapt_text(
        self,
        text: str,
        tags: Optional[List[str]] = None,
        include_tags_in_text: bool = True,
    ) -> AdaptedContent:
        """
        Adapt raw text for the platform.

        Args:
            text: Raw text to adapt
            tags: Optional hashtags
            include_tags_in_text: Whether to append tags to text

        Returns:
            AdaptedContent
        """
        tag_list = (tags or [])[:self.limits.max_tags]
        original_length = len(text)

        # Calculate space needed for tags
        if include_tags_in_text and tag_list:
            tags_text = " " + " ".join(f"#{t}" for t in tag_list)
            available_length = self.limits.max_text_length - len(tags_text)
        else:
            tags_text = ""
            available_length = self.limits.max_text_length

        if len(text) <= available_length:
            final_text = text + tags_text if include_tags_in_text else text
            return AdaptedContent(
                platform=self.platform,
                parts=[final_text],
                title=None,
                tags=tag_list,
                images=[],
                is_thread=False,
                original_length=original_length,
                adapted_length=len(final_text),
                truncated=False,
            )

        # Need to split or truncate
        if self.limits.supports_threads:
            parts = self._split_into_thread(text, tag_list if include_tags_in_text else [])
            return AdaptedContent(
                platform=self.platform,
                parts=parts,
                title=None,
                tags=tag_list,
                images=[],
                is_thread=True,
                original_length=original_length,
                adapted_length=sum(len(p) for p in parts),
                truncated=False,
            )
        else:
            truncated = self._smart_truncate(text, available_length)
            final_text = truncated + tags_text if include_tags_in_text else truncated
            return AdaptedContent(
                platform=self.platform,
                parts=[final_text],
                title=None,
                tags=tag_list,
                images=[],
                is_thread=False,
                original_length=original_length,
                adapted_length=len(final_text),
                truncated=True,
            )

    def _split_into_thread(
        self,
        text: str,
        tags: List[str],
    ) -> List[str]:
        """Split long text into a thread of posts."""
        parts = []
        max_len = self.limits.max_text_length
        connector = self.limits.thread_connector

        # Reserve space for thread indicator (e.g., "1/5 🧵")
        indicator_space = 10  # e.g., "10/10 🧵 "
        effective_max = max_len - indicator_space

        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        current_part = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If paragraph itself is too long, split by sentences
            if len(para) > effective_max:
                # Split by sentence endings
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if len(current_part) + len(sentence) + 1 <= effective_max:
                        current_part = f"{current_part} {sentence}".strip()
                    else:
                        if current_part:
                            parts.append(current_part)
                        # If single sentence is too long, hard split
                        if len(sentence) > effective_max:
                            while len(sentence) > effective_max:
                                parts.append(sentence[:effective_max-3] + "...")
                                sentence = sentence[effective_max-3:]
                            current_part = sentence
                        else:
                            current_part = sentence
            else:
                # Try to add paragraph to current part
                test_text = f"{current_part}\n\n{para}" if current_part else para
                if len(test_text) <= effective_max:
                    current_part = test_text
                else:
                    if current_part:
                        parts.append(current_part)
                    current_part = para

        if current_part:
            parts.append(current_part)

        # Add thread indicators
        total = len(parts)
        if total > 1:
            parts = [
                f"{i+1}/{total} {connector}\n{part}" if i < total - 1 else f"{i+1}/{total}\n{part}"
                for i, part in enumerate(parts)
            ]

        # Add tags to last part if they fit
        if tags and parts:
            tags_text = "\n" + " ".join(f"#{t}" for t in tags[:5])
            if len(parts[-1]) + len(tags_text) <= max_len:
                parts[-1] += tags_text

        return parts

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Split on sentence endings, keeping the punctuation
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        return [s.strip() for s in sentences if s.strip()]

    def _smart_truncate(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Truncate text intelligently at sentence or word boundaries.
        """
        max_len = max_length or self.limits.max_text_length
        ellipsis = "..."
        available = max_len - len(ellipsis)

        if len(text) <= max_len:
            return text

        # Try to truncate at sentence boundary
        truncated = text[:available]

        # Find last sentence ending
        for ending in ["。", "！", "？", ".", "!", "?"]:
            last_pos = truncated.rfind(ending)
            if last_pos > available * 0.5:  # At least half the content
                return truncated[:last_pos + 1]

        # Fall back to word boundary (space or Chinese char)
        last_space = truncated.rfind(" ")
        if last_space > available * 0.7:
            return truncated[:last_space] + ellipsis

        # Hard truncate
        return truncated + ellipsis


def get_adapter(platform: str) -> ContentAdapter:
    """Get a content adapter for the specified platform."""
    return ContentAdapter(platform)


def get_platform_limits(platform: str) -> PlatformLimits:
    """Get limits for a platform."""
    return PLATFORM_LIMITS.get(platform.lower(), PLATFORM_LIMITS.get("bluesky"))
