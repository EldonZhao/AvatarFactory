"""
Video composer - Creates slideshow videos from images and audio.

Uses MoviePy for video composition with support for:
- Image slideshows with audio narration
- Text card generation for content without images
- Fade transitions between slides
"""

import os
import re
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple

from .base import VideoError


def _import_moviepy():
    """Import moviepy classes, supporting both v1.x and v2.x."""
    try:
        # MoviePy 2.x
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
        return ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
    except ImportError:
        try:
            # MoviePy 1.x
            from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
            return ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
        except ImportError:
            raise VideoError(
                "moviepy not installed. Install with: pip install moviepy"
            )


class VideoComposer:
    """Compose slideshow videos from images and audio."""

    def __init__(
        self,
        background_color: str = "#FFFFFF",
        font_path: Optional[str] = None,
        font_size: int = 48,
        font_color: str = "#333333",
    ):
        """
        Initialize video composer.

        Args:
            background_color: Default background color (hex)
            font_path: Path to TTF font file for text cards
            font_size: Font size for text cards
            font_color: Font color for text (hex)
        """
        self.background_color = background_color
        self.font_path = font_path
        self.font_size = font_size
        self.font_color = font_color

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    async def create_slideshow(
        self,
        images: List[Path],
        audio_path: Path,
        output_path: Path,
        image_duration: float = 5.0,
        transition_duration: float = 0.5,
        fps: int = 24,
    ) -> Path:
        """
        Create a slideshow video from images with audio.

        Args:
            images: List of image file paths
            audio_path: Path to audio file
            output_path: Path for output video
            image_duration: Duration per image in seconds (if no audio)
            transition_duration: Fade transition duration
            fps: Video frames per second

        Returns:
            Path to the created video
        """
        ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips = _import_moviepy()

        if not images:
            raise VideoError("No images provided for slideshow")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load audio to get duration
        audio_clip = AudioFileClip(str(audio_path))
        total_duration = audio_clip.duration

        # Calculate duration per image
        num_images = len(images)
        # Account for transitions overlapping
        total_transition_time = (num_images - 1) * transition_duration
        available_time = total_duration - total_transition_time
        duration_per_image = max(available_time / num_images, 1.0)

        # Create image clips
        clips = []
        for i, img_path in enumerate(images):
            img_clip = ImageClip(str(img_path))
            img_clip = img_clip.with_duration(duration_per_image + transition_duration)
            img_clip = img_clip.resized(height=720)  # Standardize height

            # Add fade in/out for smooth transitions
            if i > 0:
                img_clip = img_clip.with_effects([_crossfadein(transition_duration)])
            if i < num_images - 1:
                img_clip = img_clip.with_effects([_crossfadeout(transition_duration)])

            clips.append(img_clip)

        # Concatenate with crossfade
        if len(clips) > 1:
            video = concatenate_videoclips(
                clips,
                method="compose",
                padding=-transition_duration,
            )
        else:
            video = clips[0]

        # Trim or loop to match audio duration
        if video.duration < total_duration:
            # Loop the video if it's shorter than audio
            video = _loop_clip(video, duration=total_duration)
        elif video.duration > total_duration:
            video = video.subclipped(0, total_duration)

        # Add audio
        video = video.with_audio(audio_clip)

        # Write video file
        video.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            logger=None,  # Suppress moviepy logs
        )

        # Cleanup
        audio_clip.close()
        video.close()
        for clip in clips:
            clip.close()

        return output_path

    async def create_text_cards(
        self,
        text: str,
        output_dir: Path,
        max_chars_per_card: int = 200,
        card_size: Tuple[int, int] = (1280, 720),
        padding: int = 80,
    ) -> List[Path]:
        """
        Create text card images from content text.

        Splits long text into multiple cards.

        Args:
            text: Full text content
            output_dir: Directory to save card images
            max_chars_per_card: Maximum characters per card
            card_size: Card dimensions (width, height)
            padding: Padding around text

        Returns:
            List of paths to generated card images
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            raise VideoError(
                "Pillow not installed. Install with: pip install Pillow"
            )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Split text into sections
        sections = self._split_text_to_sections(text, max_chars_per_card)

        card_paths = []
        width, height = card_size
        bg_color = self._hex_to_rgb(self.background_color)
        text_color = self._hex_to_rgb(self.font_color)

        # Try to load font
        font = self._get_font()

        for i, section in enumerate(sections):
            # Create card image
            img = Image.new("RGB", (width, height), bg_color)
            draw = ImageDraw.Draw(img)

            # Calculate text wrapping
            text_area_width = width - (padding * 2)
            wrapped_text = self._wrap_text(section, font, text_area_width, draw)

            # Calculate vertical position (center)
            text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
            text_height = text_bbox[3] - text_bbox[1]
            y_position = (height - text_height) // 2

            # Draw text
            draw.text(
                (padding, y_position),
                wrapped_text,
                fill=text_color,
                font=font,
            )

            # Add page indicator
            page_text = f"{i + 1}/{len(sections)}"
            page_bbox = draw.textbbox((0, 0), page_text, font=font)
            page_x = width - padding - (page_bbox[2] - page_bbox[0])
            draw.text(
                (page_x, height - padding),
                page_text,
                fill=(150, 150, 150),
                font=font,
            )

            # Save card
            card_path = output_dir / f"card_{i + 1:03d}.png"
            img.save(card_path)
            card_paths.append(card_path)

        return card_paths

    def _get_font(self) -> "ImageFont.FreeTypeFont":
        """Get font for text rendering."""
        try:
            from PIL import ImageFont
        except ImportError:
            raise VideoError("Pillow not installed")

        if self.font_path and os.path.exists(self.font_path):
            return ImageFont.truetype(self.font_path, self.font_size)

        # Try common system fonts for Chinese
        system_fonts = [
            # Windows
            "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei
            "C:/Windows/Fonts/simhei.ttf",  # SimHei
            "C:/Windows/Fonts/simsun.ttc",  # SimSun
            # macOS
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            # Linux
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]

        for font_path in system_fonts:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, self.font_size)
                except Exception:
                    continue

        # Fallback to default font
        try:
            return ImageFont.truetype("arial.ttf", self.font_size)
        except Exception:
            return ImageFont.load_default()

    def _split_text_to_sections(
        self,
        text: str,
        max_chars: int,
    ) -> List[str]:
        """
        Split text into sections for cards.

        Tries to split at paragraph or sentence boundaries.
        """
        # First split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        sections = []
        current_section = ""

        for para in paragraphs:
            if len(current_section) + len(para) + 2 <= max_chars:
                if current_section:
                    current_section += "\n\n" + para
                else:
                    current_section = para
            else:
                if current_section:
                    sections.append(current_section)
                    current_section = ""

                # If paragraph itself is too long, split by sentences
                if len(para) > max_chars:
                    sentences = self._split_to_sentences(para)
                    for sentence in sentences:
                        if len(current_section) + len(sentence) + 1 <= max_chars:
                            if current_section:
                                current_section += " " + sentence
                            else:
                                current_section = sentence
                        else:
                            if current_section:
                                sections.append(current_section)
                            current_section = sentence
                else:
                    current_section = para

        if current_section:
            sections.append(current_section)

        return sections if sections else [text[:max_chars]]

    def _split_to_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Handle Chinese and English sentence endings
        pattern = r"([。！？.!?]+)"
        parts = re.split(pattern, text)

        sentences = []
        current = ""
        for part in parts:
            current += part
            if re.match(pattern, part):
                sentences.append(current.strip())
                current = ""

        if current.strip():
            sentences.append(current.strip())

        return sentences

    def _wrap_text(
        self,
        text: str,
        font: "ImageFont.FreeTypeFont",
        max_width: int,
        draw: "ImageDraw.Draw",
    ) -> str:
        """Wrap text to fit within max width."""
        lines = []

        for paragraph in text.split("\n"):
            if not paragraph:
                lines.append("")
                continue

            # For Chinese text, wrap by character
            current_line = ""
            for char in paragraph:
                test_line = current_line + char
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]

                if line_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char

            if current_line:
                lines.append(current_line)

        return "\n".join(lines)

    async def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of an audio file in seconds."""
        _, AudioFileClip, _, _ = _import_moviepy()

        audio = AudioFileClip(str(audio_path))
        duration = audio.duration
        audio.close()
        return duration


def _crossfadein(duration: float):
    """Create crossfade in effect for MoviePy 2.x."""
    try:
        from moviepy.video.fx import CrossFadeIn
        return CrossFadeIn(duration)
    except ImportError:
        # Fallback - return a no-op for older versions
        return None


def _crossfadeout(duration: float):
    """Create crossfade out effect for MoviePy 2.x."""
    try:
        from moviepy.video.fx import CrossFadeOut
        return CrossFadeOut(duration)
    except ImportError:
        # Fallback - return a no-op for older versions
        return None


def _loop_clip(clip, duration: float):
    """Loop a clip to reach target duration, supporting MoviePy 2.x."""
    try:
        from moviepy.video.fx import Loop
        return clip.with_effects([Loop(duration=duration)])
    except ImportError:
        # MoviePy 1.x fallback
        return clip.loop(duration=duration)
