"""
Unit tests for multimodal support.

Tests cover:
- ContentType enum
- Content model with content_type field
- MediaAttachment with mime_type
- LLM provider multimodal (vision) support
- ContentAgent content_type handling
- Image resolution helper
"""

import os
import tempfile
from typing import List, Optional

import pytest

from avatarfactory.models.schemas import (
    Content,
    ContentType,
    MediaAttachment,
    PlatformType,
)
from avatarfactory.core.llm_provider import (
    BaseLLMProvider,
    _resolve_image_content,
)

# ============================================================================
# ContentType Enum Tests
# ============================================================================


class TestContentType:
    """Tests for ContentType enum"""

    def test_content_type_values(self):
        """Test all ContentType enum values exist"""
        assert ContentType.TEXT == "text"
        assert ContentType.IMAGE_TEXT == "image_text"
        assert ContentType.VIDEO == "video"

    def test_content_type_from_string(self):
        """Test creating ContentType from string"""
        assert ContentType("text") == ContentType.TEXT
        assert ContentType("image_text") == ContentType.IMAGE_TEXT
        assert ContentType("video") == ContentType.VIDEO

    def test_content_type_invalid(self):
        """Test invalid ContentType raises error"""
        with pytest.raises(ValueError):
            ContentType("invalid_type")

    def test_content_type_is_string(self):
        """Test ContentType is a string enum"""
        assert isinstance(ContentType.TEXT, str)
        assert ContentType.TEXT.value == "text"


# ============================================================================
# Content Model Tests
# ============================================================================


class TestContentMultimodal:
    """Tests for Content model multimodal fields"""

    def test_default_content_type_is_text(self):
        """Test that content_type defaults to TEXT"""
        content = Content(
            id="test_001",
            persona_id="persona_001",
            title="Test Title",
            body="Test body",
            pillar="Test Pillar",
            platform=PlatformType.XIAOHONGSHU,
        )
        assert content.content_type == ContentType.TEXT

    def test_content_type_image_text(self):
        """Test creating content with IMAGE_TEXT type"""
        content = Content(
            id="test_002",
            persona_id="persona_001",
            title="Image Post",
            body="Visual content body",
            pillar="Visual Pillar",
            platform=PlatformType.XIAOHONGSHU,
            content_type=ContentType.IMAGE_TEXT,
        )
        assert content.content_type == ContentType.IMAGE_TEXT

    def test_content_type_video(self):
        """Test creating content with VIDEO type"""
        content = Content(
            id="test_003",
            persona_id="persona_001",
            title="Video Script",
            body="Narration text for video",
            pillar="Video Pillar",
            platform=PlatformType.DOUYIN,
            content_type=ContentType.VIDEO,
        )
        assert content.content_type == ContentType.VIDEO

    def test_content_serialization_with_content_type(self):
        """Test that content_type is included in serialization"""
        content = Content(
            id="test_004",
            persona_id="persona_001",
            title="Test",
            body="Test body",
            pillar="Pillar",
            platform=PlatformType.TWITTER,
            content_type=ContentType.IMAGE_TEXT,
        )
        data = content.model_dump()
        assert data["content_type"] == "image_text"

    def test_content_deserialization_with_content_type(self):
        """Test that content_type is correctly deserialized"""
        data = {
            "id": "test_005",
            "persona_id": "persona_001",
            "title": "Test",
            "body": "Body",
            "pillar": "Pillar",
            "platform": "twitter",
            "content_type": "video",
        }
        content = Content(**data)
        assert content.content_type == ContentType.VIDEO

    def test_backward_compatible_without_content_type(self):
        """Test that Content without content_type still works (defaults to TEXT)"""
        data = {
            "id": "test_006",
            "persona_id": "persona_001",
            "title": "Legacy Content",
            "body": "Body",
            "pillar": "Pillar",
            "platform": "xiaohongshu",
        }
        content = Content(**data)
        assert content.content_type == ContentType.TEXT


# ============================================================================
# MediaAttachment Tests
# ============================================================================


class TestMediaAttachmentMultimodal:
    """Tests for MediaAttachment multimodal enhancements"""

    def test_default_media_attachment(self):
        """Test default MediaAttachment values"""
        media = MediaAttachment()
        assert media.type == "image"
        assert media.mime_type is None

    def test_media_attachment_with_mime_type(self):
        """Test MediaAttachment with mime_type"""
        media = MediaAttachment(
            type="image",
            url="https://example.com/photo.jpg",
            mime_type="image/jpeg",
            alt_text="A photo",
        )
        assert media.mime_type == "image/jpeg"
        assert media.type == "image"

    def test_video_media_attachment(self):
        """Test video MediaAttachment"""
        media = MediaAttachment(
            type="video",
            path="/path/to/video.mp4",
            mime_type="video/mp4",
            caption="Demo video",
        )
        assert media.type == "video"
        assert media.mime_type == "video/mp4"

    def test_audio_media_attachment(self):
        """Test audio MediaAttachment"""
        media = MediaAttachment(
            type="audio",
            path="/path/to/audio.mp3",
            mime_type="audio/mpeg",
        )
        assert media.type == "audio"
        assert media.mime_type == "audio/mpeg"

    def test_media_attachment_serialization(self):
        """Test MediaAttachment serialization includes mime_type"""
        media = MediaAttachment(
            type="image",
            url="https://example.com/img.png",
            mime_type="image/png",
        )
        data = media.model_dump()
        assert data["mime_type"] == "image/png"


# ============================================================================
# Image Resolution Helper Tests
# ============================================================================


class TestResolveImageContent:
    """Tests for _resolve_image_content helper"""

    def test_resolve_url_http(self):
        """Test resolving HTTP URL"""
        result = _resolve_image_content("http://example.com/image.jpg")
        assert result["type"] == "url"
        assert result["url"] == "http://example.com/image.jpg"

    def test_resolve_url_https(self):
        """Test resolving HTTPS URL"""
        result = _resolve_image_content("https://example.com/image.png")
        assert result["type"] == "url"
        assert result["url"] == "https://example.com/image.png"

    def test_resolve_data_uri(self):
        """Test resolving data URI"""
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
        result = _resolve_image_content(data_uri)
        assert result["type"] == "base64"
        assert result["data_uri"] == data_uri

    def test_resolve_local_file(self):
        """Test resolving local file path"""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            temp_path = f.name

        try:
            result = _resolve_image_content(temp_path)
            assert result["type"] == "base64"
            assert result["mime_type"] == "image/png"
            assert "base64_data" in result
            assert result["data_uri"].startswith("data:image/png;base64,")
        finally:
            os.unlink(temp_path)

    def test_resolve_local_jpeg(self):
        """Test resolving local JPEG file"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            temp_path = f.name

        try:
            result = _resolve_image_content(temp_path)
            assert result["mime_type"] == "image/jpeg"
        finally:
            os.unlink(temp_path)

    def test_resolve_local_webp(self):
        """Test resolving local WebP file"""
        with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            temp_path = f.name

        try:
            result = _resolve_image_content(temp_path)
            assert result["mime_type"] == "image/webp"
        finally:
            os.unlink(temp_path)

    def test_resolve_nonexistent_file_raises(self):
        """Test that nonexistent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            _resolve_image_content("/nonexistent/path/image.png")

    def test_resolve_large_file_raises(self):
        """Test that a file exceeding size limit raises ValueError"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write 21 MB of data (exceeds 20 MB limit)
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * (21 * 1024 * 1024))
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="too large"):
                _resolve_image_content(temp_path)
        finally:
            os.unlink(temp_path)


# ============================================================================
# LLM Provider Multimodal Tests
# ============================================================================


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing multimodal signature"""

    def __init__(self) -> None:
        super().__init__(model="mock-model")
        self.last_call_images: Optional[List[str]] = None

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        images: Optional[List[str]] = None,
    ) -> str:
        self.last_call_images = images
        return "Mock response"

    def validate_config(self) -> bool:
        return True


class TestLLMProviderMultimodal:
    """Tests for LLM provider multimodal support"""

    @pytest.mark.asyncio
    async def test_generate_without_images(self):
        """Test generate works without images (backward compatible)"""
        provider = MockLLMProvider()
        result = await provider.generate(prompt="Hello")
        assert result == "Mock response"
        assert provider.last_call_images is None

    @pytest.mark.asyncio
    async def test_generate_with_images(self):
        """Test generate accepts images parameter"""
        provider = MockLLMProvider()
        images = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        result = await provider.generate(prompt="Describe these images", images=images)
        assert result == "Mock response"
        assert provider.last_call_images == images

    @pytest.mark.asyncio
    async def test_generate_with_empty_images(self):
        """Test generate with empty images list"""
        provider = MockLLMProvider()
        result = await provider.generate(prompt="Hello", images=[])
        assert result == "Mock response"

    def test_provider_signature_includes_images(self):
        """Test that BaseLLMProvider.generate has images parameter"""
        import inspect

        sig = inspect.signature(BaseLLMProvider.generate)
        assert "images" in sig.parameters
        param = sig.parameters["images"]
        assert param.default is None


# ============================================================================
# ContentAgent Multimodal Tests
# ============================================================================


class TestContentAgentMultimodal:
    """Tests for ContentAgent multimodal content generation"""

    def test_get_video_json_fields_text(self):
        """Test _get_video_json_fields returns empty for text"""
        from avatarfactory.agents.content import ContentAgent
        from avatarfactory.core.knowledges import KnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(tmpdir)
            agent = ContentAgent(
                knowledge_base=kb,
                llm_provider=MockLLMProvider(),
            )
            result = agent._get_video_json_fields(ContentType.TEXT)
            assert result == ""

    def test_get_video_json_fields_video(self):
        """Test _get_video_json_fields returns fields for video"""
        from avatarfactory.agents.content import ContentAgent
        from avatarfactory.core.knowledges import KnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(tmpdir)
            agent = ContentAgent(
                knowledge_base=kb,
                llm_provider=MockLLMProvider(),
            )
            result = agent._get_video_json_fields(ContentType.VIDEO)
            assert "scene_descriptions" in result
            assert "narration_style" in result

    def test_prepare_video_metadata(self):
        """Test _prepare_video_metadata adds video config"""
        from avatarfactory.agents.content import ContentAgent
        from avatarfactory.core.knowledges import KnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(tmpdir)
            agent = ContentAgent(
                knowledge_base=kb,
                llm_provider=MockLLMProvider(),
            )

            content = Content(
                id="test_video_001",
                persona_id="persona_001",
                title="Video Content",
                body="This is narration text for the video.",
                pillar="Video Pillar",
                platform=PlatformType.DOUYIN,
                content_type=ContentType.VIDEO,
                metadata={
                    "scene_descriptions": ["Scene 1", "Scene 2"],
                },
            )

            # Need to save the content first so _prepare_video_metadata can update it
            kb.save_content(content, status="draft")

            result = agent._prepare_video_metadata(content)
            assert "video_config" in result.metadata
            assert result.metadata["video_config"]["video_type"] == "slideshow"
            assert result.metadata["video_config"]["scene_count"] == 2
            assert result.metadata["video_config"]["narration_text"] == content.body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
