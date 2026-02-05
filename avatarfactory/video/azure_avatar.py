"""
Azure Avatar provider - Azure Speech Avatar batch synthesis.

Uses Azure's batch avatar synthesis REST API to generate digital human videos.

Requires:
- AZURE_SPEECH_KEY environment variable
- AZURE_SPEECH_REGION environment variable (must support avatar synthesis)

Available regions: westus2, westeurope, southeastasia
"""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .base import AvatarProvider, TTSError


# Available avatar characters
AVATAR_CHARACTERS = {
    "lisa": {
        "id": "lisa",
        "name": "Lisa",
        "description": "Professional female avatar",
        "style": "casual-sitting",
    },
    "grace": {
        "id": "grace",
        "name": "Grace",
        "description": "Friendly female avatar",
        "style": "graceful-standing",
    },
    "harry": {
        "id": "harry",
        "name": "Harry",
        "description": "Professional male avatar",
        "style": "casual-sitting",
    },
    "max": {
        "id": "max",
        "name": "Max",
        "description": "Casual male avatar",
        "style": "casual",
    },
}


class AzureAvatarProvider(AvatarProvider):
    """
    Azure Avatar provider for digital human video generation.

    Uses batch synthesis API - suitable for generating pre-recorded videos.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """
        Initialize Azure Avatar provider.

        Args:
            api_key: Azure Speech API key
            region: Azure region (westus2, westeurope, or southeastasia)
        """
        self.api_key = api_key or os.getenv("AZURE_SPEECH_KEY")
        self.region = region or os.getenv("AZURE_SPEECH_REGION", "westus2")
        self.base_url = f"https://{self.region}.api.cognitive.microsoft.com"

    @property
    def name(self) -> str:
        return "azure-avatar"

    def is_available(self) -> bool:
        """Check if Azure Avatar is configured."""
        return bool(self.api_key)

    async def list_avatars(self) -> List[Dict[str, str]]:
        """List available avatar characters."""
        return [
            {
                "id": avatar["id"],
                "name": avatar["name"],
                "description": avatar["description"],
            }
            for avatar in AVATAR_CHARACTERS.values()
        ]

    async def generate_avatar_video(
        self,
        text: str,
        voice: str,
        avatar_character: str,
        output_path: Path,
        background_color: str = "#FFFFFF",
        video_format: str = "mp4",
        video_codec: str = "h264",
        subtitle: bool = False,
    ) -> Path:
        """
        Generate avatar video using Azure batch synthesis API.

        Args:
            text: Text for avatar to speak
            voice: Voice ID (e.g., "zh-CN-XiaoxuanNeural")
            avatar_character: Avatar character name (lisa, grace, harry, max)
            output_path: Path to save the video
            background_color: Background color hex code
            video_format: Output format (mp4, webm)
            video_codec: Video codec (h264, hevc, vp9)
            subtitle: Whether to include subtitles

        Returns:
            Path to the generated video file
        """
        if not self.api_key:
            raise TTSError(
                "Azure Speech API key not configured. "
                "Set AZURE_SPEECH_KEY environment variable."
            )

        avatar = AVATAR_CHARACTERS.get(avatar_character.lower())
        if not avatar:
            available = ", ".join(AVATAR_CHARACTERS.keys())
            raise TTSError(
                f"Unknown avatar character: {avatar_character}. "
                f"Available: {available}"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create synthesis job
        job_id = await self._create_synthesis_job(
            text=text,
            voice=voice,
            avatar_character=avatar["id"],
            avatar_style=avatar["style"],
            background_color=background_color,
            video_format=video_format,
            video_codec=video_codec,
            subtitle=subtitle,
        )

        # Poll for completion
        video_url = await self._wait_for_completion(job_id)

        # Download the video
        await self._download_video(video_url, output_path)

        return output_path

    async def _create_synthesis_job(
        self,
        text: str,
        voice: str,
        avatar_character: str,
        avatar_style: str,
        background_color: str,
        video_format: str,
        video_codec: str,
        subtitle: bool,
    ) -> str:
        """Create a batch avatar synthesis job."""
        job_id = str(uuid.uuid4())
        url = f"{self.base_url}/avatar/batchsyntheses/{job_id}?api-version=2024-04-15-preview"

        # Prepare SSML
        ssml = self._create_ssml(text, voice)

        payload = {
            "synthesisConfig": {
                "voice": voice,
            },
            "inputKind": "SSML",
            "inputs": [
                {"content": ssml}
            ],
            "avatarConfig": {
                "talkingAvatarCharacter": avatar_character,
                "talkingAvatarStyle": avatar_style,
                "videoFormat": video_format,
                "videoCodec": video_codec,
                "subtitleType": "soft_embedded" if subtitle else "none",
                "backgroundColor": background_color,
            },
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                json=payload,
                headers=headers,
                timeout=60,
            )

            if response.status_code not in (200, 201, 202):
                raise TTSError(
                    f"Failed to create avatar synthesis job: "
                    f"{response.status_code} - {response.text}"
                )

            return job_id

    async def _wait_for_completion(
        self,
        job_id: str,
        timeout_seconds: int = 600,
        poll_interval: int = 10,
    ) -> str:
        """
        Poll for synthesis job completion.

        Returns the URL to download the video.
        """
        url = f"{self.base_url}/avatar/batchsyntheses/{job_id}?api-version=2024-04-15-preview"
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        elapsed = 0
        async with httpx.AsyncClient() as client:
            while elapsed < timeout_seconds:
                response = await client.get(url, headers=headers, timeout=30)

                if response.status_code != 200:
                    raise TTSError(
                        f"Failed to check synthesis status: "
                        f"{response.status_code} - {response.text}"
                    )

                data = response.json()
                status = data.get("status", "").lower()

                if status == "succeeded":
                    # Get the video URL from outputs
                    outputs = data.get("outputs", {})
                    video_url = outputs.get("result")
                    if not video_url:
                        raise TTSError(
                            "Synthesis succeeded but no video URL in response"
                        )
                    return video_url

                elif status == "failed":
                    error = data.get("properties", {}).get("error", {})
                    raise TTSError(
                        f"Avatar synthesis failed: "
                        f"{error.get('code', 'Unknown')} - {error.get('message', 'No details')}"
                    )

                elif status in ("notstarted", "running"):
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                else:
                    raise TTSError(f"Unknown synthesis status: {status}")

        raise TTSError(
            f"Avatar synthesis timed out after {timeout_seconds} seconds"
        )

    async def _download_video(self, video_url: str, output_path: Path) -> None:
        """Download the synthesized video."""
        async with httpx.AsyncClient() as client:
            response = await client.get(video_url, timeout=300)

            if response.status_code != 200:
                raise TTSError(
                    f"Failed to download video: {response.status_code}"
                )

            with open(output_path, "wb") as f:
                f.write(response.content)

    def _create_ssml(self, text: str, voice: str) -> str:
        """Create SSML for avatar synthesis."""
        text_escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        return f"""
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
    <voice name="{voice}">
        {text_escaped}
    </voice>
</speak>
""".strip()

    async def delete_synthesis_job(self, job_id: str) -> bool:
        """Delete a synthesis job (cleanup)."""
        url = f"{self.base_url}/avatar/batchsyntheses/{job_id}?api-version=2024-04-15-preview"
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers, timeout=30)
            return response.status_code in (200, 204)
