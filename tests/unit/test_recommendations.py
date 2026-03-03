"""
Tests for recommendation system.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.models.schemas import (
    RecommendedPersona,
    RecommendationStatus,
    TrendSnapshot,
)


@pytest.fixture
def temp_kb():
    """Create a temporary knowledge base for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = KnowledgeBase(tmpdir)
        yield kb


class TestRecommendedPersonaModel:
    """Test RecommendedPersona model."""

    def test_create_recommended_persona(self):
        """Test creating a RecommendedPersona."""
        rec = RecommendedPersona(
            id="rec_persona_test123",
            name="Tech Blogger",
            tagline="Making AI accessible to everyone",
            domain="technology",
            expertise=["AI", "Machine Learning", "Python"],
            target_audience="Software developers",
            audience_pain_points=["Keeping up with AI trends"],
            suggested_tone="professional",
            content_types=["tutorials", "reviews"],
            content_pillars=["AI tutorials", "Tool reviews"],
            relevance_score=85.0,
            potential_score=90.0,
            rationale="High demand for AI content",
            source_platforms=["bluesky", "twitter"],
            source_trends=["AI", "LLM", "ChatGPT"],
        )

        assert rec.id == "rec_persona_test123"
        assert rec.name == "Tech Blogger"
        assert rec.domain == "technology"
        assert rec.status == RecommendationStatus.ACTIVE
        assert rec.relevance_score == 85.0
        assert rec.potential_score == 90.0

    def test_recommendation_status_enum(self):
        """Test recommendation status values."""
        assert RecommendationStatus.ACTIVE == "active"
        assert RecommendationStatus.ADOPTED == "adopted"
        assert RecommendationStatus.ARCHIVED == "archived"


class TestTrendSnapshotModel:
    """Test TrendSnapshot model."""

    def test_create_trend_snapshot(self):
        """Test creating a TrendSnapshot."""
        snapshot = TrendSnapshot(
            id="snap_test123",
            platform="bluesky",
            trending_topics=["AI", "Machine Learning", "Python"],
            trending_hashtags=["#AI", "#ML", "#Python"],
            top_posts=[
                {"body": "AI is transforming...", "likes": 100},
                {"body": "New Python release...", "likes": 80},
            ],
            analysis_summary="AI and Python topics are trending",
            key_themes=["artificial intelligence", "programming"],
            content_patterns=["tutorials", "news"],
        )

        assert snapshot.id == "snap_test123"
        assert snapshot.platform == "bluesky"
        assert len(snapshot.trending_topics) == 3
        assert len(snapshot.top_posts) == 2


class TestKnowledgeBaseRecommendations:
    """Test KnowledgeBase recommendation methods."""

    def test_save_and_get_recommended_personas(self, temp_kb):
        """Test saving and retrieving recommended personas."""
        personas = [
            RecommendedPersona(
                id="rec_persona_001",
                name="AI Blogger",
                tagline="AI insights daily",
                domain="technology",
                target_audience="Tech enthusiasts",
                relevance_score=80.0,
                potential_score=85.0,
            ),
            RecommendedPersona(
                id="rec_persona_002",
                name="Lifestyle Guru",
                tagline="Living your best life",
                domain="lifestyle",
                target_audience="Young professionals",
                relevance_score=75.0,
                potential_score=80.0,
            ),
        ]

        # Save
        path = temp_kb.save_recommended_personas(personas)
        assert Path(path).exists()

        # Retrieve
        retrieved = temp_kb.get_recommended_personas(limit=10)
        assert len(retrieved) == 2
        assert retrieved[0].id == "rec_persona_001"
        assert retrieved[1].id == "rec_persona_002"

    def test_get_latest_recommendations(self, temp_kb):
        """Test getting latest active recommendations."""
        personas = [
            RecommendedPersona(
                id="rec_persona_active",
                name="Active Persona",
                tagline="Active",
                domain="tech",
                target_audience="All",
                status=RecommendationStatus.ACTIVE,
            ),
        ]
        temp_kb.save_recommended_personas(personas)

        latest = temp_kb.get_latest_recommendations(limit=5)
        assert len(latest) == 1
        assert latest[0].status == RecommendationStatus.ACTIVE

    def test_get_recommendation_by_id(self, temp_kb):
        """Test getting a specific recommendation by ID."""
        personas = [
            RecommendedPersona(
                id="rec_persona_find_me",
                name="Find Me",
                tagline="Test",
                domain="test",
                target_audience="Testers",
            ),
        ]
        temp_kb.save_recommended_personas(personas)

        # Find by ID
        found = temp_kb.get_recommendation("rec_persona_find_me")
        assert found is not None
        assert found.name == "Find Me"

        # Not found
        not_found = temp_kb.get_recommendation("rec_persona_nonexistent")
        assert not_found is None

    def test_mark_recommendation_adopted(self, temp_kb):
        """Test marking a recommendation as adopted."""
        personas = [
            RecommendedPersona(
                id="rec_persona_to_adopt",
                name="To Adopt",
                tagline="Will be adopted",
                domain="test",
                target_audience="All",
            ),
        ]
        temp_kb.save_recommended_personas(personas)

        # Mark as adopted
        result = temp_kb.mark_recommendation_adopted(
            "rec_persona_to_adopt", "persona_new_123"
        )
        assert result is True

        # Verify status changed
        rec = temp_kb.get_recommendation("rec_persona_to_adopt")
        assert rec.status == RecommendationStatus.ADOPTED
        assert rec.adopted_persona_id == "persona_new_123"

    def test_filter_by_domain(self, temp_kb):
        """Test filtering recommendations by domain."""
        personas = [
            RecommendedPersona(
                id="rec_tech",
                name="Tech",
                tagline="Tech",
                domain="technology",
                target_audience="All",
            ),
            RecommendedPersona(
                id="rec_life",
                name="Life",
                tagline="Life",
                domain="lifestyle",
                target_audience="All",
            ),
        ]
        temp_kb.save_recommended_personas(personas)

        # Filter by domain
        tech_only = temp_kb.get_recommended_personas(domain="technology")
        assert len(tech_only) == 1
        assert tech_only[0].domain == "technology"


class TestKnowledgeBaseTrendSnapshots:
    """Test KnowledgeBase trend snapshot methods."""

    def test_save_and_get_trend_snapshot(self, temp_kb):
        """Test saving and retrieving trend snapshots."""
        snapshot = TrendSnapshot(
            id="snap_test",
            platform="bluesky",
            trending_topics=["AI", "Python"],
            analysis_summary="Tech topics trending",
        )

        # Save
        path = temp_kb.save_trend_snapshot(snapshot)
        assert Path(path).exists()

        # Retrieve
        snapshots = temp_kb.get_latest_trend_snapshots(limit=5)
        assert len(snapshots) == 1
        assert snapshots[0].id == "snap_test"

    def test_filter_by_platform(self, temp_kb):
        """Test filtering snapshots by platform."""
        snap1 = TrendSnapshot(
            id="snap_bluesky",
            platform="bluesky",
            trending_topics=["topic1"],
        )
        snap2 = TrendSnapshot(
            id="snap_twitter",
            platform="twitter",
            trending_topics=["topic2"],
        )

        temp_kb.save_trend_snapshot(snap1)
        temp_kb.save_trend_snapshot(snap2)

        # Filter by platform
        bluesky_only = temp_kb.get_latest_trend_snapshots(platform="bluesky")
        assert len(bluesky_only) == 1
        assert bluesky_only[0].platform == "bluesky"

    def test_get_today_snapshots(self, temp_kb):
        """Test getting today's snapshots."""
        snapshot = TrendSnapshot(
            id="snap_today",
            platform="bluesky",
            captured_at=datetime.now(),
            trending_topics=["today_topic"],
        )
        temp_kb.save_trend_snapshot(snapshot)

        today = temp_kb.get_today_trend_snapshots()
        assert len(today) == 1
        assert today[0].id == "snap_today"
