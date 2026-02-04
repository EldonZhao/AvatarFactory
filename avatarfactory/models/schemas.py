"""
Data models for AvatarFactory.

All data structures are defined using Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================


class PlatformType(str, Enum):
    """Supported social media platforms"""

    XIAOHONGSHU = "xiaohongshu"
    ZHIHU = "zhihu"
    TWITTER = "twitter"
    DOUYIN = "douyin"


class ContentPillarFrequency(str, Enum):
    """Content pillar posting frequency"""

    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class RiskLevel(str, Enum):
    """Content risk levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    """Agent task types"""

    CHAT = "chat"
    CREATE_PERSONA = "create_persona"
    UPDATE_PERSONA = "update_persona"
    GENERATE_CONTENT = "generate_content"
    REVIEW_CONTENT = "review_content"
    PREDICT_ENGAGEMENT = "predict_engagement"
    ANALYZE_DATA = "analyze_data"


# ============================================================================
# Persona Models
# ============================================================================


class Identity(BaseModel):
    """Persona identity configuration"""

    name: str = Field(..., description="Persona name/title")
    tagline: str = Field(..., description="One-line positioning statement")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")


class TargetAudience(BaseModel):
    """Target audience definition"""

    primary: str = Field(..., description="Primary audience description")
    pain_points: List[str] = Field(default_factory=list, description="Audience pain points")
    goals: List[str] = Field(default_factory=list, description="Audience goals")


class VoiceStyle(BaseModel):
    """Voice and tone configuration"""

    tone: str = Field(..., description="Overall tone (e.g., professional, casual)")
    language_patterns: List[str] = Field(
        default_factory=list, description="Language patterns to follow"
    )
    emoji_usage: str = Field(default="moderate", description="Emoji usage guidance")


class ContentPillar(BaseModel):
    """Content pillar definition"""

    name: str = Field(..., description="Pillar name")
    description: str = Field(default="", description="Pillar description")
    frequency: str = Field(default="weekly", description="Posting frequency")
    examples: List[str] = Field(default_factory=list, description="Example topics")


class Boundaries(BaseModel):
    """Content boundaries and compliance rules"""

    avoid: List[str] = Field(default_factory=list, description="Topics/patterns to avoid")
    compliance: List[str] = Field(
        default_factory=list, description="Compliance requirements"
    )


class Persona(BaseModel):
    """Complete persona configuration"""

    id: str = Field(..., description="Unique persona ID")
    version: str = Field(default="v1.0", description="Persona version")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    identity: Identity
    target_audience: TargetAudience
    voice_style: VoiceStyle
    content_pillars: List[ContentPillar]
    boundaries: Boundaries

    platforms: List[PlatformType] = Field(
        default_factory=list, description="Target platforms"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PersonaVersion(BaseModel):
    """Persona version history record"""

    version: str
    timestamp: datetime
    changes: List[str] = Field(..., description="What changed")
    reason: str = Field(..., description="Why changed")
    expected_impact: str = Field(..., description="Expected impact")
    author: str = Field(default="user", description="Who made the change")
    approved: bool = Field(default=False, description="Whether approved by user")


# ============================================================================
# Content Models
# ============================================================================


class ContentStructure(BaseModel):
    """Content structure definition"""

    sections: List[str] = Field(..., description="Content sections in order")
    style_constraints: Dict[str, Any] = Field(
        default_factory=dict, description="Style constraints"
    )


class Content(BaseModel):
    """Generated content"""

    id: str = Field(..., description="Unique content ID")
    persona_id: str = Field(..., description="Associated persona ID")
    created_at: datetime = Field(default_factory=datetime.now)

    title: str = Field(..., description="Content title")
    body: str = Field(..., description="Content body")
    pillar: str = Field(..., description="Content pillar")
    platform: PlatformType = Field(..., description="Target platform")

    structure: Optional[ContentStructure] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Review results (populated after review)
    review_score: Optional[float] = None
    review_issues: List[str] = Field(default_factory=list)

    # Prediction results (populated after simulation)
    predicted_engagement: Optional[Dict[str, Any]] = None


# ============================================================================
# Review Models
# ============================================================================


class DimensionScore(BaseModel):
    """Score for a specific review dimension"""

    score: int = Field(..., ge=0, le=100, description="Score 0-100")
    issues: List[str] = Field(default_factory=list, description="Identified issues")
    strengths: List[str] = Field(default_factory=list, description="Identified strengths")
    reasoning: List[str] = Field(default_factory=list, description="Reasoning for score")


class ComplianceCheck(BaseModel):
    """Compliance check result"""

    score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    checks: Dict[str, str] = Field(
        default_factory=dict, description="Individual check results (pass/fail)"
    )
    issues: List[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """Complete review report for content"""

    content_id: str
    reviewed_at: datetime = Field(default_factory=datetime.now)

    persona_consistency: DimensionScore
    platform_fit: DimensionScore
    compliance: ComplianceCheck
    engagement_potential: DimensionScore

    overall_score: int = Field(..., ge=0, le=100, description="Overall score")

    suggestions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Suggestions by priority (critical/recommended/optional)",
    )


# ============================================================================
# Simulation Models
# ============================================================================


class EngagementRange(BaseModel):
    """Engagement metric prediction range"""

    min: int = Field(..., ge=0)
    likely: int = Field(..., ge=0)
    max: int = Field(..., ge=0)


class EngagementPrediction(BaseModel):
    """Engagement prediction for content"""

    views: EngagementRange
    likes: EngagementRange
    comments: EngagementRange
    saves: EngagementRange

    confidence: str = Field(..., description="Prediction confidence (low/medium/high)")
    confidence_factors: Dict[str, float] = Field(default_factory=dict)

    ranking_factors: Dict[str, int] = Field(
        default_factory=dict, description="Ranking factors 1-10"
    )


class CommentScenario(BaseModel):
    """Possible comment scenario"""

    text: str = Field(..., description="Comment text")
    probability: float = Field(..., ge=0, le=1, description="Probability 0-1")
    suggested_reply: Optional[str] = None


class SimulationReport(BaseModel):
    """Simulation report for content"""

    content_id: str
    simulated_at: datetime = Field(default_factory=datetime.now)

    engagement_prediction: EngagementPrediction
    comment_scenarios: Dict[str, List[CommentScenario]] = Field(
        default_factory=dict, description="Scenarios by category (positive/questions/challenges)"
    )


# ============================================================================
# Experiment Models
# ============================================================================


class ExperimentVariant(BaseModel):
    """Experiment variant (A/B test)"""

    id: str
    type: str = Field(..., description="Variant type/name")
    content_ids: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(
        default_factory=dict, description="Collected metrics"
    )


class Experiment(BaseModel):
    """Experiment definition and results"""

    id: str
    persona_id: str
    created_at: datetime = Field(default_factory=datetime.now)

    hypothesis: str = Field(..., description="What we're testing")
    period: str = Field(..., description="Time period (e.g., '2024-W08')")

    variants: List[ExperimentVariant]
    conclusion: Optional[str] = None
    statistical_significance: Optional[float] = None
    next_actions: List[str] = Field(default_factory=list)


class WeeklyRetrospective(BaseModel):
    """Weekly retrospective report"""

    week: str = Field(..., description="Week identifier (e.g., '2024-W08')")
    persona_id: str
    generated_at: datetime = Field(default_factory=datetime.now)

    summary: Dict[str, Any] = Field(default_factory=dict)
    what_worked: List[str] = Field(default_factory=list)
    what_didnt: List[str] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    next_week_plan: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Agent Message Models
# ============================================================================


class AgentMessage(BaseModel):
    """Message passed between agents"""

    sender: str = Field(..., description="Sender agent ID")
    receiver: str = Field(..., description="Receiver agent ID")
    task_type: TaskType = Field(..., description="Task type")

    payload: Dict[str, Any] = Field(default_factory=dict, description="Task data")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Context (persona_id, etc.)"
    )

    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Intent Models
# ============================================================================


class Intent(BaseModel):
    """User intent parsed by Orchestrator"""

    intent_type: str = Field(
        ...,
        description="Intent type (create_persona/generate_content/analyze_data/optimize_persona)",
    )
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0, le=1)
