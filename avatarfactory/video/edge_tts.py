"""
Edge TTS provider - Free Microsoft Edge text-to-speech.

Uses the edge-tts library which interfaces with Microsoft's Edge browser TTS service.
No API key required.
"""

from pathlib import Path
from typing import List, Optional
from importlib.util import find_spec

from .base import TTSProvider, TTSError, VoiceInfo


class EdgeTTSProvider(TTSProvider):
    """Free TTS provider using Microsoft Edge's TTS service."""

    @property
    def name(self) -> str:
        return "edge"

    def is_available(self) -> bool:
        """Check if edge-tts is installed."""
        return find_spec("edge_tts") is not None

    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> Path:
        """
        Synthesize text to speech using Edge TTS.

        Args:
            text: Text to synthesize
            voice: Voice ID (e.g., "zh-CN-XiaoxuanNeural")
            output_path: Path to save the MP3 audio file
            rate: Speech rate (e.g., "+20%", "-10%")
            pitch: Pitch adjustment (e.g., "+5Hz", "-10Hz")

        Returns:
            Path to the generated audio file
        """
        try:
            import edge_tts
        except ImportError:
            raise TTSError("edge-tts not installed. Install with: pip install edge-tts")

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create communicate object with voice and adjustments
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                pitch=pitch,
            )

            # Save to file
            await communicate.save(str(output_path))

            if not output_path.exists():
                raise TTSError(f"Failed to create audio file: {output_path}")

            return output_path

        except Exception as e:
            if isinstance(e, TTSError):
                raise
            raise TTSError(f"Edge TTS synthesis failed: {e}")

    async def list_voices(self, locale: Optional[str] = None) -> List[VoiceInfo]:
        """
        List available voices from Edge TTS.

        Args:
            locale: Filter by locale (e.g., "zh-CN", "en-US")

        Returns:
            List of available voices
        """
        try:
            import edge_tts
        except ImportError:
            raise TTSError("edge-tts not installed. Install with: pip install edge-tts")

        try:
            voices = await edge_tts.list_voices()

            result = []
            for voice in voices:
                voice_locale = voice.get("Locale", "")

                # Filter by locale if specified
                if locale and not voice_locale.startswith(locale):
                    continue

                result.append(
                    VoiceInfo(
                        id=voice.get("ShortName", ""),
                        name=voice.get("FriendlyName", voice.get("ShortName", "")),
                        gender=voice.get("Gender", "Unknown"),
                        locale=voice_locale,
                        style=None,  # Edge TTS doesn't expose styles in the API
                        provider=self.name,
                    )
                )

            return result

        except Exception as e:
            raise TTSError(f"Failed to list Edge TTS voices: {e}")


# Common Chinese voices for quick reference
CHINESE_VOICES = {
    "xiaoxuan": "zh-CN-XiaoxuanNeural",  # Female, bright/活泼
    "yunxi": "zh-CN-YunxiNeural",  # Male, professional
    "xiaohan": "zh-CN-XiaohanNeural",  # Female, warm
    "yunyang": "zh-CN-YunyangNeural",  # Male, energetic
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",  # Female, assistant
    "xiaoyi": "zh-CN-XiaoyiNeural",  # Female, gentle
    "yunjian": "zh-CN-YunjianNeural",  # Male, narration
    "yunhao": "zh-CN-YunhaoNeural",  # Male, advertisement
}

# Common English voices
ENGLISH_VOICES = {
    "jenny": "en-US-JennyNeural",  # Female, assistant
    "aria": "en-US-AriaNeural",  # Female, news
    "guy": "en-US-GuyNeural",  # Male, news
    "davis": "en-US-DavisNeural",  # Male, conversational
}


def get_recommended_voice(language: str = "zh-CN", style: str = "default") -> str:
    """
    Get a recommended voice for the given language and style.

    Args:
        language: Language code (zh-CN, en-US, etc.)
        style: Style hint (bright, professional, warm, etc.)

    Returns:
        Voice ID string
    """
    if language.startswith("zh"):
        style_map = {
            "default": CHINESE_VOICES["xiaoxuan"],
            "bright": CHINESE_VOICES["xiaoxuan"],
            "professional": CHINESE_VOICES["yunxi"],
            "warm": CHINESE_VOICES["xiaohan"],
            "energetic": CHINESE_VOICES["yunyang"],
            "narration": CHINESE_VOICES["yunjian"],
        }
        return style_map.get(style, CHINESE_VOICES["xiaoxuan"])

    elif language.startswith("en"):
        style_map = {
            "default": ENGLISH_VOICES["jenny"],
            "news": ENGLISH_VOICES["aria"],
            "professional": ENGLISH_VOICES["guy"],
            "conversational": ENGLISH_VOICES["davis"],
        }
        return style_map.get(style, ENGLISH_VOICES["jenny"])

    # Default fallback
    return "zh-CN-XiaoxuanNeural"
