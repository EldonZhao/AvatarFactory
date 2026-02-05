"""
Video generation module for AvatarFactory.

Supports TTS (Text-to-Speech) and video composition using:
- Azure TTS + Avatar (Premium)
- Azure TTS + Slideshow (Standard)
- Edge TTS + Slideshow (Free fallback)
"""

from .generator import VideoGenerator
from .base import TTSProvider, VideoConfig, VideoResult

__all__ = ["VideoGenerator", "TTSProvider", "VideoConfig", "VideoResult"]
