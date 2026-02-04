"""
Basic functionality tests for AvatarFactory.
"""

import pytest
from avatarfactory.core.knowledge_base import KnowledgeBase
from avatarfactory.models.schemas import (
    Boundaries,
    ContentPillar,
    Identity,
    Persona,
    TargetAudience,
    VoiceStyle,
    PlatformType,
)
from datetime import datetime
import tempfile
import shutil


@pytest.fixture
def temp_kb():
    """Create a temporary knowledge base for testing"""
    temp_dir = tempfile.mkdtemp()
    kb = KnowledgeBase(temp_dir)
    yield kb
    shutil.rmtree(temp_dir)


def test_knowledge_base_creation(temp_kb):
    """Test that knowledge base creates proper directory structure"""
    assert temp_kb.base_path.exists()
    assert (temp_kb.base_path / "personas").exists()
    assert (temp_kb.base_path / "content_library").exists()


def test_persona_creation_and_loading(temp_kb):
    """Test creating and loading a persona"""
    persona = Persona(
        id="test_persona_001",
        version="v1.0",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        identity=Identity(
            name="Test Persona",
            tagline="Test tagline",
            expertise=["testing", "development"],
        ),
        target_audience=TargetAudience(
            primary="developers",
            pain_points=["testing pain"],
            goals=["better tests"],
        ),
        voice_style=VoiceStyle(
            tone="professional",
            language_patterns=["clear", "concise"],
            emoji_usage="minimal",
        ),
        content_pillars=[
            ContentPillar(
                name="tutorials",
                description="how-to guides",
                frequency="weekly",
            )
        ],
        boundaries=Boundaries(
            avoid=["spam"],
            compliance=["cite sources"],
        ),
        platforms=[PlatformType.XIAOHONGSHU],
    )

    # Save
    temp_kb.save_persona(persona)

    # Load
    loaded = temp_kb.load_persona("test_persona_001")
    assert loaded is not None
    assert loaded.id == "test_persona_001"
    assert loaded.identity.name == "Test Persona"


def test_list_personas(temp_kb):
    """Test listing personas"""
    # Initially empty
    assert len(temp_kb.list_personas()) == 0

    # Create two personas
    for i in range(2):
        persona = Persona(
            id=f"persona_{i}",
            version="v1.0",
            identity=Identity(name=f"Persona {i}", tagline="test", expertise=[]),
            target_audience=TargetAudience(primary="test", pain_points=[], goals=[]),
            voice_style=VoiceStyle(tone="test", language_patterns=[], emoji_usage="test"),
            content_pillars=[],
            boundaries=Boundaries(avoid=[], compliance=[]),
            platforms=[PlatformType.XIAOHONGSHU],
        )
        temp_kb.save_persona(persona)

    # Should have 2 personas
    personas = temp_kb.list_personas()
    assert len(personas) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
