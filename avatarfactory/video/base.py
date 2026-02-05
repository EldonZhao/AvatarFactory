"""
Base classes for video generation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class VideoType(str, Enum):
    """Type of video to generate."""
    SLIDESHOW = "slideshow"
    AVATAR = "avatar"


class TTSProviderType(str, Enum):
    """Supported TTS providers."""
    AZURE = "azure"
    EDGE = "edge"
    AUTO = "auto"


@dataclass
class VoiceInfo:
    """Information about an available voice."""
    id: str
    name: str
    gender: str
    locale: str
    style: Optional[str] = None
    provider: str = "unknown"

    def __str__(self) -> str:
        return f"{self.id} ({self.name}, {self.gender}, {self.locale})"


@dataclass
class VideoConfig:
    """Configuration for video generation."""
    video_type: VideoType = VideoType.SLIDESHOW
    voice: str = "zh-CN-XiaoxuanNeural"
    avatar_character: Optional[str] = None  # For avatar type: lisa, grace, etc.
    output_path: Optional[Path] = None

    # TTS settings
    rate: str = "+0%"  # Speech rate adjustment
    pitch: str = "+0Hz"  # Pitch adjustment

    # Slideshow settings
    image_duration: float = 5.0  # Seconds per image
    transition_duration: float = 0.5  # Fade transition duration
    background_color: str = "#FFFFFF"

    # Text card settings (when no images)
    font_size: int = 48
    font_color: str = "#333333"
    max_chars_per_card: int = 200


@dataclass
class VideoResult:
    """Result of video generation."""
    success: bool
    video_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_formatted(self) -> str:
        """Return duration in MM:SS format."""
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> Path:
        """
        Synthesize text to speech audio.

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            output_path: Path to save audio file
            rate: Speech rate adjustment (e.g., "+10%", "-5%")
            pitch: Pitch adjustment (e.g., "+5Hz", "-10Hz")

        Returns:
            Path to the generated audio file

        Raises:
            TTSError: If synthesis fails
        """
        pass

    @abstractmethod
    async def list_voices(self, locale: Optional[str] = None) -> List[VoiceInfo]:
        """
        List available voices.

        Args:
            locale: Filter by locale (e.g., "zh-CN", "en-US")

        Returns:
            List of available voices
        """
        pass

    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        return True


class AvatarProvider(ABC):
    """Abstract base class for avatar video providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def generate_avatar_video(
        self,
        text: str,
        voice: str,
        avatar_character: str,
        output_path: Path,
    ) -> Path:
        """
        Generate avatar video with speech.

        Args:
            text: Text for the avatar to speak
            voice: Voice ID to use
            avatar_character: Avatar character name
            output_path: Path to save video file

        Returns:
            Path to the generated video file
        """
        pass

    @abstractmethod
    async def list_avatars(self) -> List[Dict[str, str]]:
        """List available avatar characters."""
        pass


class TTSError(Exception):
    """Exception raised for TTS-related errors."""
    pass


class VideoError(Exception):
    """Exception raised for video generation errors."""
    pass
