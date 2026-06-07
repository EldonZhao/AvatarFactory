"""
Azure TTS provider - Azure Cognitive Services Speech SDK.

Requires:
- azure-cognitiveservices-speech package
- AZURE_SPEECH_KEY environment variable
- AZURE_SPEECH_REGION environment variable
"""

import os
from importlib.util import find_spec
from pathlib import Path
from typing import Any, List, Optional

from .base import TTSProvider, TTSError, VoiceInfo


class AzureTTSProvider(TTSProvider):
    """TTS provider using Azure Cognitive Services Speech SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """
        Initialize Azure TTS provider.

        Args:
            api_key: Azure Speech API key (defaults to AZURE_SPEECH_KEY env var)
            region: Azure region (defaults to AZURE_SPEECH_REGION env var)
        """
        self.api_key = api_key or os.getenv("AZURE_SPEECH_KEY")
        self.region = region or os.getenv("AZURE_SPEECH_REGION", "eastasia")

    @property
    def name(self) -> str:
        return "azure"

    def is_available(self) -> bool:
        """Check if Azure Speech SDK is installed and configured."""
        return bool(self.api_key) and find_spec("azure.cognitiveservices.speech") is not None

    def _get_speech_config(self) -> Any:
        """Get Azure Speech configuration."""
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise TTSError(
                "azure-cognitiveservices-speech not installed. "
                "Install with: pip install azure-cognitiveservices-speech"
            )

        if not self.api_key:
            raise TTSError(
                "Azure Speech API key not configured. " "Set AZURE_SPEECH_KEY environment variable."
            )

        speech_config = speechsdk.SpeechConfig(
            subscription=self.api_key,
            region=self.region,
        )
        return speech_config

    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> Path:
        """
        Synthesize text to speech using Azure TTS.

        Args:
            text: Text to synthesize
            voice: Voice ID (e.g., "zh-CN-XiaoxuanNeural")
            output_path: Path to save the audio file
            rate: Speech rate adjustment
            pitch: Pitch adjustment

        Returns:
            Path to the generated audio file
        """
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise TTSError(
                "azure-cognitiveservices-speech not installed. "
                "Install with: pip install azure-cognitiveservices-speech"
            )

        import asyncio

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        speech_config = self._get_speech_config()
        speech_config.speech_synthesis_voice_name = voice

        # Set audio output format
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))

        # Create SSML for more control over speech
        ssml = self._create_ssml(text, voice, rate, pitch)

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        # Run synthesis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: synthesizer.speak_ssml_async(ssml).get())

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_path
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            raise TTSError(
                f"Azure TTS synthesis canceled: {cancellation.reason}. "
                f"Error details: {cancellation.error_details}"
            )
        else:
            raise TTSError(f"Azure TTS synthesis failed: {result.reason}")

    def _create_ssml(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> str:
        """
        Create SSML markup for speech synthesis.

        Args:
            text: Text content
            voice: Voice ID
            rate: Speech rate
            pitch: Pitch adjustment

        Returns:
            SSML string
        """
        # Escape special XML characters
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        ssml = f"""
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
    <voice name="{voice}">
        <prosody rate="{rate}" pitch="{pitch}">
            {text}
        </prosody>
    </voice>
</speak>
""".strip()
        return ssml

    async def list_voices(self, locale: Optional[str] = None) -> List[VoiceInfo]:
        """
        List available voices from Azure TTS.

        Args:
            locale: Filter by locale (e.g., "zh-CN", "en-US")

        Returns:
            List of available voices
        """
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise TTSError(
                "azure-cognitiveservices-speech not installed. "
                "Install with: pip install azure-cognitiveservices-speech"
            )

        import asyncio

        speech_config = self._get_speech_config()
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None,  # No audio output needed
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: synthesizer.get_voices_async().get())

        if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
            voices = []
            for voice in result.voices:
                # Filter by locale if specified
                if locale and not voice.locale.startswith(locale):
                    continue

                voices.append(
                    VoiceInfo(
                        id=voice.short_name,
                        name=voice.local_name,
                        gender=(
                            voice.gender.name
                            if hasattr(voice.gender, "name")
                            else str(voice.gender)
                        ),
                        locale=voice.locale,
                        style=None,  # Could extract from voice.style_list
                        provider=self.name,
                    )
                )
            return voices
        else:
            raise TTSError(f"Failed to list Azure voices: {result.reason}")

    async def synthesize_with_style(
        self,
        text: str,
        voice: str,
        output_path: Path,
        style: str = "general",
        style_degree: float = 1.0,
    ) -> Path:
        """
        Synthesize with speaking style (Azure-specific feature).

        Args:
            text: Text to synthesize
            voice: Voice ID
            output_path: Output path
            style: Speaking style (e.g., "cheerful", "sad", "angry")
            style_degree: Style intensity 0.01 to 2.0 (default 1.0)

        Returns:
            Path to generated audio
        """
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise TTSError(
                "azure-cognitiveservices-speech not installed. "
                "Install with: pip install azure-cognitiveservices-speech"
            )

        import asyncio

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        speech_config = self._get_speech_config()
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))

        # SSML with style
        text_escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ssml = f"""
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
    <voice name="{voice}">
        <mstts:express-as style="{style}" styledegree="{style_degree}">
            {text_escaped}
        </mstts:express-as>
    </voice>
</speak>
""".strip()

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: synthesizer.speak_ssml_async(ssml).get())

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_path
        else:
            raise TTSError(f"Azure TTS styled synthesis failed: {result.reason}")
