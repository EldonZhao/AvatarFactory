"""
Video generator - Main orchestrator for video generation.

Coordinates TTS providers, avatar providers, and video composition.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from .base import (
    TTSProvider,
    TTSProviderType,
    VideoConfig,
    VideoResult,
    VideoType,
    VoiceInfo,
    TTSError,
    VideoError,
)
from .edge_tts import EdgeTTSProvider
from .azure_tts import AzureTTSProvider
from .azure_avatar import AzureAvatarProvider
from .composer import VideoComposer


class VideoGenerator:
    """
    Main orchestrator for video generation.

    Supports:
    - Slideshow videos with TTS narration
    - Avatar videos (digital human speaking)
    - Automatic provider selection based on availability
    """

    def __init__(
        self,
        tts_provider: Union[str, TTSProviderType] = TTSProviderType.AUTO,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize video generator.

        Args:
            tts_provider: TTS provider to use ("auto", "azure", "edge")
            output_dir: Base output directory for videos
        """
        self.output_dir = Path(
            output_dir or os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
        ) / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize providers
        self._tts_provider: Optional[TTSProvider] = None
        self._avatar_provider: Optional[AzureAvatarProvider] = None
        self._composer: Optional[VideoComposer] = None

        # Determine TTS provider
        provider_type = (
            TTSProviderType(tts_provider)
            if isinstance(tts_provider, str)
            else tts_provider
        )
        self._init_providers(provider_type)

    def _init_providers(self, provider_type: TTSProviderType) -> None:
        """Initialize TTS and avatar providers based on configuration."""
        if provider_type == TTSProviderType.AUTO:
            # Try Azure first, fall back to Edge
            azure = AzureTTSProvider()
            if azure.is_available():
                self._tts_provider = azure
            else:
                edge = EdgeTTSProvider()
                if edge.is_available():
                    self._tts_provider = edge

        elif provider_type == TTSProviderType.AZURE:
            self._tts_provider = AzureTTSProvider()

        elif provider_type == TTSProviderType.EDGE:
            self._tts_provider = EdgeTTSProvider()

        # Initialize avatar provider if Azure is configured
        avatar = AzureAvatarProvider()
        if avatar.is_available():
            self._avatar_provider = avatar

        # Initialize video composer
        self._composer = VideoComposer()

    @property
    def tts_provider(self) -> TTSProvider:
        """Get the active TTS provider."""
        if not self._tts_provider:
            raise TTSError("No TTS provider available")
        return self._tts_provider

    @property
    def composer(self) -> VideoComposer:
        """Get the video composer."""
        if not self._composer:
            self._composer = VideoComposer()
        return self._composer

    async def generate(
        self,
        content_id: str,
        text: str,
        config: Optional[VideoConfig] = None,
        images: Optional[List[Path]] = None,
    ) -> VideoResult:
        """
        Generate video from text content.

        Args:
            content_id: Unique content identifier
            text: Text content for TTS/video
            config: Video configuration options
            images: Optional list of image paths for slideshow

        Returns:
            VideoResult with video path and metadata
        """
        config = config or VideoConfig()

        # Create output directory for this content
        content_dir = self.output_dir / content_id
        content_dir.mkdir(parents=True, exist_ok=True)

        try:
            if config.video_type == VideoType.AVATAR:
                return await self._generate_avatar_video(
                    text=text,
                    config=config,
                    output_dir=content_dir,
                )
            else:
                return await self._generate_slideshow_video(
                    text=text,
                    config=config,
                    images=images,
                    output_dir=content_dir,
                )
        except (TTSError, VideoError) as e:
            return VideoResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            return VideoResult(
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def _generate_slideshow_video(
        self,
        text: str,
        config: VideoConfig,
        images: Optional[List[Path]],
        output_dir: Path,
    ) -> VideoResult:
        """Generate slideshow video with TTS narration."""
        audio_path = output_dir / "audio.mp3"
        video_path = config.output_path or (output_dir / "video_slideshow.mp4")

        # Step 1: Generate TTS audio
        await self.tts_provider.synthesize(
            text=text,
            voice=config.voice,
            output_path=audio_path,
            rate=config.rate,
            pitch=config.pitch,
        )

        # Step 2: Prepare images
        if not images:
            # Generate text cards if no images provided
            images = await self.composer.create_text_cards(
                text=text,
                output_dir=output_dir / "cards",
                max_chars_per_card=config.max_chars_per_card,
            )

        # Validate images exist
        valid_images = [img for img in images if Path(img).exists()]
        if not valid_images:
            raise VideoError("No valid images for slideshow")

        # Step 3: Compose video
        await self.composer.create_slideshow(
            images=valid_images,
            audio_path=audio_path,
            output_path=video_path,
            image_duration=config.image_duration,
            transition_duration=config.transition_duration,
        )

        # Get video duration
        duration = await self.composer.get_audio_duration(audio_path)

        # Save metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "video_type": "slideshow",
            "voice": config.voice,
            "tts_provider": self.tts_provider.name,
            "image_count": len(valid_images),
            "duration_seconds": duration,
        }
        self._save_metadata(output_dir / "metadata.json", metadata)

        return VideoResult(
            success=True,
            video_path=video_path,
            audio_path=audio_path,
            duration_seconds=duration,
            metadata=metadata,
        )

    async def _generate_avatar_video(
        self,
        text: str,
        config: VideoConfig,
        output_dir: Path,
    ) -> VideoResult:
        """Generate avatar (digital human) video."""
        if not self._avatar_provider:
            raise VideoError(
                "Azure Avatar provider not available. "
                "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables."
            )

        if not config.avatar_character:
            raise VideoError(
                "Avatar character not specified. "
                "Use --avatar option (e.g., lisa, grace, harry)"
            )

        video_path = config.output_path or (output_dir / "video_avatar.mp4")

        # Generate avatar video
        await self._avatar_provider.generate_avatar_video(
            text=text,
            voice=config.voice,
            avatar_character=config.avatar_character,
            output_path=video_path,
        )

        # Get approximate duration (estimate from text length)
        # Average Chinese speech: ~3 characters per second
        estimated_duration = len(text) / 3.0

        metadata = {
            "generated_at": datetime.now().isoformat(),
            "video_type": "avatar",
            "voice": config.voice,
            "avatar_character": config.avatar_character,
            "duration_seconds": estimated_duration,
        }
        self._save_metadata(output_dir / "metadata.json", metadata)

        return VideoResult(
            success=True,
            video_path=video_path,
            duration_seconds=estimated_duration,
            metadata=metadata,
        )

    async def list_voices(
        self,
        locale: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> List[VoiceInfo]:
        """
        List available voices.

        Args:
            locale: Filter by locale (e.g., "zh-CN")
            provider: Specific provider ("azure" or "edge")

        Returns:
            List of available voices
        """
        if provider == "edge":
            edge = EdgeTTSProvider()
            return await edge.list_voices(locale)
        elif provider == "azure":
            azure = AzureTTSProvider()
            return await azure.list_voices(locale)
        else:
            # Use current provider
            return await self.tts_provider.list_voices(locale)

    async def list_avatars(self) -> List[dict]:
        """List available avatar characters."""
        if self._avatar_provider:
            return await self._avatar_provider.list_avatars()
        return []

    def _save_metadata(self, path: Path, metadata: dict) -> None:
        """Save metadata to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get_provider_info(self) -> dict:
        """Get information about available providers."""
        return {
            "tts_provider": self._tts_provider.name if self._tts_provider else None,
            "tts_available": self._tts_provider is not None,
            "avatar_available": self._avatar_provider is not None and self._avatar_provider.is_available(),
            "edge_available": EdgeTTSProvider().is_available(),
            "azure_available": AzureTTSProvider().is_available(),
        }


async def generate_video_from_content(
    content_id: str,
    text: str,
    video_type: str = "slideshow",
    voice: str = "zh-CN-XiaoxuanNeural",
    provider: str = "auto",
    avatar_character: Optional[str] = None,
    images: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> VideoResult:
    """
    Convenience function to generate video from content.

    Args:
        content_id: Content identifier
        text: Text content for narration
        video_type: "slideshow" or "avatar"
        voice: Voice ID
        provider: "auto", "azure", or "edge"
        avatar_character: Avatar character for avatar videos
        images: List of image paths for slideshow
        output_path: Custom output path

    Returns:
        VideoResult
    """
    generator = VideoGenerator(tts_provider=provider)

    config = VideoConfig(
        video_type=VideoType(video_type),
        voice=voice,
        avatar_character=avatar_character,
        output_path=Path(output_path) if output_path else None,
    )

    image_paths = [Path(p) for p in images] if images else None

    return await generator.generate(
        content_id=content_id,
        text=text,
        config=config,
        images=image_paths,
    )
