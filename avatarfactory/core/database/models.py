"""
SQLAlchemy ORM models for AvatarFactory.

These models map to the database schema and provide type-safe data access.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    type_annotation_map = {
        Dict[str, Any]: JSON,
        List[str]: JSON,
        List[Dict[str, Any]]: JSON,
    }


class PersonaModel(Base):
    """Persona configuration model."""

    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[str] = mapped_column(String(16), default="v1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Identity info (flattened for common queries)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[Optional[str]] = mapped_column(Text)
    expertise: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Configuration (JSON for complex structures)
    identity: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    target_audience: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    voice_style: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_pillars: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    boundaries: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Optional configurations
    notification: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    evolution: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    agent_configs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Metadata
    platforms: Mapped[Optional[List[str]]] = mapped_column(JSON)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    versions: Mapped[List["PersonaVersionModel"]] = relationship(
        back_populates="persona", cascade="all, delete-orphan"
    )
    contents: Mapped[List["ContentModel"]] = relationship(
        back_populates="persona", cascade="all, delete-orphan"
    )
    discovery_results: Mapped[List["DiscoveryResultModel"]] = relationship(
        back_populates="persona", cascade="all, delete-orphan"
    )
    evolution_suggestions: Mapped[List["EvolutionSuggestionModel"]] = relationship(
        back_populates="persona", cascade="all, delete-orphan"
    )
    scheduled_tasks: Mapped[List["ScheduledTaskModel"]] = relationship(
        back_populates="persona", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_personas_created_at", "created_at"),
        Index("idx_personas_name", "name"),
    )


class PersonaVersionModel(Base):
    """Persona version history model."""

    __tablename__ = "persona_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    persona_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    changes: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(64), default="user")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Relationships
    persona: Mapped["PersonaModel"] = relationship(back_populates="versions")

    __table_args__ = (Index("idx_persona_versions_persona", "persona_id", "timestamp"),)


class ContentModel(Base):
    """Content model."""

    __tablename__ = "contents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Core fields (flattened for queries)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    pillar: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="text")

    # Status
    status: Mapped[str] = mapped_column(String(32), default="draft")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Structured data
    structure: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Media
    media: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    image_prompts: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Review results (denormalized for list queries)
    review_score: Mapped[Optional[float]] = mapped_column(Float)
    review_issues: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Prediction results
    predicted_engagement: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Metadata
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)

    # Relationships
    persona: Mapped["PersonaModel"] = relationship(back_populates="contents")
    review: Mapped[Optional["ReviewModel"]] = relationship(
        back_populates="content", cascade="all, delete-orphan", uselist=False
    )
    simulation: Mapped[Optional["SimulationModel"]] = relationship(
        back_populates="content", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("idx_contents_persona_status", "persona_id", "status", "created_at"),
        Index("idx_contents_platform", "platform", "created_at"),
        Index("idx_contents_created_at", "created_at"),
    )


class ReviewModel(Base):
    """Content review model."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contents.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Flattened scores for aggregation queries
    persona_consistency_score: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    compliance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    engagement_potential_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Detailed data
    persona_consistency: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    platform_fit: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    compliance: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    engagement_potential: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Suggestions
    suggestions: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)

    # Relationships
    content: Mapped["ContentModel"] = relationship(back_populates="review")

    __table_args__ = (Index("idx_reviews_overall_score", "overall_score"),)


class SimulationModel(Base):
    """Content simulation model."""

    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contents.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    simulated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Prediction data
    engagement_prediction: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    comment_scenarios: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)

    # Relationships
    content: Mapped["ContentModel"] = relationship(back_populates="simulation")


class DiscoveryResultModel(Base):
    """Discovery result model."""

    __tablename__ = "discovery_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    persona_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Analysis counts
    trending_count: Mapped[int] = mapped_column(Integer, default=0)
    ideas_count: Mapped[int] = mapped_column(Integer, default=0)

    # Full data
    pattern_analysis: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    ideas: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    persona_suggestions: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Relationships
    persona: Mapped["PersonaModel"] = relationship(back_populates="discovery_results")

    __table_args__ = (
        Index("idx_discovery_persona_platform", "persona_id", "platform", "created_at"),
    )


class EvolutionSuggestionModel(Base):
    """Evolution suggestion model."""

    __tablename__ = "evolution_suggestions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Change target
    target: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str] = mapped_column(String(32), nullable=False)

    # Suggestion content
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    current_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    proposed_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Analysis
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    severity: Mapped[str] = mapped_column(String(16), default="moderate")

    # Evidence
    evidence: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(32), default="automated")

    # Status
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    applied_version: Mapped[Optional[str]] = mapped_column(String(16))

    # Relationships
    persona: Mapped["PersonaModel"] = relationship(back_populates="evolution_suggestions")

    __table_args__ = (Index("idx_evolution_persona_status", "persona_id", "status", "created_at"),)


class TrendSnapshotModel(Base):
    """Trend snapshot model (system-level)."""

    __tablename__ = "trend_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Trend data
    trending_topics: Mapped[Optional[List[str]]] = mapped_column(JSON)
    trending_hashtags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    top_posts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)

    # Analysis
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text)
    key_themes: Mapped[Optional[List[str]]] = mapped_column(JSON)
    content_patterns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    __table_args__ = (Index("idx_trends_platform_time", "platform", "captured_at"),)


class RecommendedPersonaModel(Base):
    """Recommended persona model."""

    __tablename__ = "recommended_personas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Source
    source_platforms: Mapped[Optional[List[str]]] = mapped_column(JSON)
    source_trends: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Persona info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[Optional[str]] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    expertise: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Audience
    target_audience: Mapped[Optional[str]] = mapped_column(Text)
    audience_pain_points: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Content strategy
    suggested_tone: Mapped[Optional[str]] = mapped_column(String(64))
    content_types: Mapped[Optional[List[str]]] = mapped_column(JSON)
    content_pillars: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Scores
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)
    potential_score: Mapped[Optional[float]] = mapped_column(Float)
    rationale: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(32), default="active")
    adopted_persona_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="SET NULL")
    )

    __table_args__ = (Index("idx_recommendations_status", "status", "created_at"),)


class ScheduledTaskModel(Base):
    """Scheduled task model."""

    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    schedule: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Optional persona association
    persona_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="CASCADE")
    )
    platform: Mapped[Optional[str]] = mapped_column(String(32))
    extra_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Execution tracking
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_status: Mapped[Optional[str]] = mapped_column(String(32))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    run_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    persona: Mapped[Optional["PersonaModel"]] = relationship(back_populates="scheduled_tasks")

    __table_args__ = (
        Index("idx_tasks_persona", "persona_id"),
        Index("idx_tasks_enabled", "enabled", "task_type"),
    )


class PublishQueueModel(Base):
    """Publish queue model."""

    __tablename__ = "publish_queue"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)

    # Scheduling
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default="pending")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Result
    error: Mapped[Optional[str]] = mapped_column(Text)
    post_url: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (Index("idx_queue_status", "status", "scheduled_time"),)


class PlatformRuleModel(Base):
    """Platform rules model."""

    __tablename__ = "platform_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    rules: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class RetrospectiveModel(Base):
    """Retrospective model."""

    __tablename__ = "retrospectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    persona_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    week: Mapped[str] = mapped_column(String(16), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Retrospective content
    summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    what_worked: Mapped[Optional[List[str]]] = mapped_column(JSON)
    what_didnt: Mapped[Optional[List[str]]] = mapped_column(JSON)
    key_insights: Mapped[Optional[List[str]]] = mapped_column(JSON)
    next_week_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    __table_args__ = (Index("idx_retrospectives_persona_week", "persona_id", "week", unique=True),)
