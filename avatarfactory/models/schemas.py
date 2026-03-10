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
    BLUESKY = "bluesky"
    MASTODON = "mastodon"
    INSTAGRAM = "instagram"
    WEIBO = "weibo"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    TOUTIAO = "toutiao"


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


class ContentType(str, Enum):
    """Content modality types - progressive multimodal support"""

    TEXT = "text"  # Text-only content
    IMAGE_TEXT = "image_text"  # Image + text content (e.g., illustrated posts)
    VIDEO = "video"  # Video content (e.g., slideshow with TTS narration)


class TaskType(str, Enum):
    """Agent task types"""

    CHAT = "chat"
    CREATE_PERSONA = "create_persona"
    UPDATE_PERSONA = "update_persona"
    GENERATE_CONTENT = "generate_content"
    REVIEW_CONTENT = "review_content"
    PREDICT_ENGAGEMENT = "predict_engagement"
    ANALYZE_DATA = "analyze_data"
    DISCOVER_TRENDING = "discover_trending"
    ANALYZE_PATTERNS = "analyze_patterns"
    GET_INSPIRATION = "get_inspiration"


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


class NotificationConfig(BaseModel):
    """Notification connector configuration for a persona"""

    enabled: bool = Field(default=False, description="Whether notifications are enabled")
    connector_type: str = Field(
        default="wecom",
        description="Connector type: wecom, slack, telegram, etc."
    )
    # Note: webhook_url is configured at system level via AVATARFACTORY_WEBHOOK_URL env var
    notify_on_content: bool = Field(
        default=True, description="Notify when content is generated"
    )
    notify_on_review: bool = Field(
        default=True, description="Include review results in notification"
    )
    notify_on_discovery: bool = Field(
        default=True, description="Notify when discovery analysis completes"
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Additional connector-specific config"
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

    # Notification settings
    notification: Optional[NotificationConfig] = Field(
        None, description="Notification connector configuration"
    )

    # Evolution settings
    evolution: Optional["EvolutionConfig"] = Field(
        None, description="Evolution configuration"
    )

    # Per-persona agent configurations
    agent_configs: Dict[str, "AgentConfig"] = Field(
        default_factory=dict,
        description="Per-agent configurations keyed by agent_type",
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


class MediaAttachment(BaseModel):
    """Media attachment for content"""

    type: str = Field(default="image", description="Media type: image, video, audio")
    url: Optional[str] = None  # Remote URL
    path: Optional[str] = None  # Local file path
    alt_text: Optional[str] = None  # Accessibility text
    caption: Optional[str] = None  # Caption/description
    mime_type: Optional[str] = None  # MIME type (e.g., image/png, video/mp4)
    blob_ref: Optional[Dict[str, Any]] = None  # Platform-specific blob reference


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
    content_type: ContentType = Field(
        default=ContentType.TEXT,
        description="Content modality type: text, image_text, or video",
    )

    structure: Optional[ContentStructure] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Media attachments
    media: List[MediaAttachment] = Field(default_factory=list, description="Images/videos")
    image_prompts: List[str] = Field(default_factory=list, description="AI image generation prompts")

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


# ============================================================================
# Discovery Models
# ============================================================================


class TrendingContent(BaseModel):
    """Trending content fetched from social platforms"""

    id: str = Field(..., description="Unique ID for this trending content")
    platform: str = Field(..., description="Source platform")
    post_id: str = Field(..., description="Original post ID on platform")

    author: str = Field(..., description="Author username/handle")
    author_id: Optional[str] = None

    title: Optional[str] = None
    body: str = Field(..., description="Content body/text")

    likes: int = Field(default=0)
    comments: int = Field(default=0)
    shares: int = Field(default=0)
    views: int = Field(default=0)

    tags: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.now)

    # Media information
    images: List[str] = Field(default_factory=list, description="Image URLs")
    image_count: int = Field(default=0, description="Number of images")
    has_media: bool = Field(default=False, description="Whether post has media")

    # Analysis results
    relevance_score: Optional[float] = None  # How relevant to persona
    pattern_tags: List[str] = Field(default_factory=list)  # Identified patterns


class ContentPattern(BaseModel):
    """Identified pattern in successful content"""

    pattern_type: str = Field(..., description="Type: hook/structure/topic/style")
    name: str = Field(..., description="Pattern name")
    description: str = Field(..., description="Pattern description")
    examples: List[str] = Field(default_factory=list, description="Example content IDs")
    frequency: int = Field(default=1, description="How often this pattern appears")
    avg_engagement: float = Field(default=0.0, description="Average engagement score")


class ContentPatternAnalysis(BaseModel):
    """Analysis of content patterns from trending content"""

    analyzed_at: datetime = Field(default_factory=datetime.now)
    platform: str
    query: Optional[str] = None
    content_count: int = Field(default=0)

    # Identified patterns
    hook_patterns: List[ContentPattern] = Field(default_factory=list)
    structure_patterns: List[ContentPattern] = Field(default_factory=list)
    topic_patterns: List[ContentPattern] = Field(default_factory=list)
    style_patterns: List[ContentPattern] = Field(default_factory=list)

    # Trending topics
    trending_topics: List[str] = Field(default_factory=list)
    trending_hashtags: List[str] = Field(default_factory=list)

    # Summary insights
    key_insights: List[str] = Field(default_factory=list)


class ContentIdea(BaseModel):
    """Content idea generated from discovery analysis"""

    id: str = Field(..., description="Unique idea ID")
    created_at: datetime = Field(default_factory=datetime.now)

    topic: str = Field(..., description="Suggested topic")
    angle: str = Field(..., description="Unique angle/perspective")
    hook: Optional[str] = None  # Suggested hook

    content_type: str = Field(default="post", description="post/thread/story/etc")
    suggested_pillar: Optional[str] = None  # Which persona pillar this fits

    reference_contents: List[str] = Field(
        default_factory=list, description="IDs of inspiring trending content"
    )

    estimated_engagement: str = Field(
        default="medium", description="low/medium/high"
    )
    reasoning: str = Field(default="", description="Why this idea could work")

    # Image/visual suggestions
    image_suggestions: List[str] = Field(
        default_factory=list, description="Descriptions of recommended images"
    )
    recommended_image_count: int = Field(
        default=2, description="Recommended number of images for this content"
    )

    # Status tracking
    status: str = Field(default="new", description="new/saved/used/discarded")


class DiscoveryReport(BaseModel):
    """Discovery session report"""

    id: str = Field(..., description="Report ID")
    persona_id: str
    created_at: datetime = Field(default_factory=datetime.now)

    platforms_searched: List[str] = Field(default_factory=list)
    queries_used: List[str] = Field(default_factory=list)

    # Results
    trending_content_count: int = Field(default=0)
    patterns_found: int = Field(default=0)
    ideas_generated: int = Field(default=0)

    # Pattern analysis
    pattern_analysis: Optional[ContentPatternAnalysis] = None

    # Generated ideas
    content_ideas: List[ContentIdea] = Field(default_factory=list)

    # Persona optimization suggestions
    persona_suggestions: List[str] = Field(default_factory=list)


# ============================================================================
# Recommendation Models
# ============================================================================


class RecommendationStatus(str, Enum):
    """Status of a recommended persona"""

    ACTIVE = "active"
    ADOPTED = "adopted"
    ARCHIVED = "archived"


class RecommendedPersona(BaseModel):
    """Recommended persona template based on trending topics"""

    id: str = Field(..., description="Unique recommendation ID (rec_persona_xxxxx)")
    created_at: datetime = Field(default_factory=datetime.now)
    source_platforms: List[str] = Field(
        default_factory=list, description="Platforms where trends were discovered"
    )
    source_trends: List[str] = Field(
        default_factory=list, description="Related trending topics"
    )

    # Core persona info
    name: str = Field(..., description="Recommended persona name")
    tagline: str = Field(..., description="One-line positioning statement")
    domain: str = Field(..., description="Domain/niche (tech, lifestyle, finance, etc.)")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")

    # Target audience
    target_audience: str = Field(..., description="Primary target audience")
    audience_pain_points: List[str] = Field(
        default_factory=list, description="Audience pain points to address"
    )

    # Style suggestions
    suggested_tone: str = Field(default="professional", description="Suggested tone")
    content_types: List[str] = Field(
        default_factory=list, description="Recommended content types"
    )
    content_pillars: List[str] = Field(
        default_factory=list, description="Suggested content pillars"
    )

    # Scoring and rationale
    relevance_score: float = Field(
        default=0.0, ge=0, le=100, description="Trend relevance score (0-100)"
    )
    potential_score: float = Field(
        default=0.0, ge=0, le=100, description="Growth potential score (0-100)"
    )
    rationale: str = Field(default="", description="Recommendation rationale")

    # Status
    status: RecommendationStatus = Field(
        default=RecommendationStatus.ACTIVE, description="Recommendation status"
    )
    adopted_persona_id: Optional[str] = Field(
        None, description="Created persona ID if adopted"
    )


class TrendSnapshot(BaseModel):
    """Snapshot of trending topics from a platform"""

    id: str = Field(..., description="Snapshot ID")
    platform: str = Field(..., description="Source platform")
    captured_at: datetime = Field(default_factory=datetime.now)

    # Trending data
    trending_topics: List[str] = Field(
        default_factory=list, description="Top trending topics"
    )
    trending_hashtags: List[str] = Field(
        default_factory=list, description="Trending hashtags"
    )
    top_posts: List[Dict[str, Any]] = Field(
        default_factory=list, description="Sample top posts"
    )

    # Analysis
    analysis_summary: str = Field(default="", description="AI analysis summary")
    key_themes: List[str] = Field(
        default_factory=list, description="Identified key themes"
    )
    content_patterns: List[str] = Field(
        default_factory=list, description="Observed content patterns"
    )


# ============================================================================
# Evolution Models
# ============================================================================


class EvolutionSeverity(str, Enum):
    """Severity level for evolution suggestions"""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class EvolutionTarget(str, Enum):
    """Target type for evolution suggestions"""

    PERSONA = "persona"
    CONTENT_AGENT = "content_agent"
    REVIEW_AGENT = "review_agent"
    DISCOVERY_AGENT = "discovery_agent"


class EvolutionArea(str, Enum):
    """Area of change for evolution suggestions"""

    IDENTITY = "identity"
    VOICE_STYLE = "voice_style"
    CONTENT_PILLARS = "content_pillars"
    BOUNDARIES = "boundaries"
    TARGET_AUDIENCE = "target_audience"
    AGENT_CONFIG = "agent_config"


class EvolutionSuggestionStatus(str, Enum):
    """Status of an evolution suggestion"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPLIED = "auto_applied"


class EvolutionSource(str, Enum):
    """Source of evolution suggestion"""

    AUTOMATED = "automated"
    USER_FEEDBACK = "user_feedback"
    DISCOVERY = "discovery"


class EvolutionSuggestion(BaseModel):
    """Evolution suggestion for persona or agent improvement"""

    id: str = Field(..., description="Unique suggestion ID")
    created_at: datetime = Field(default_factory=datetime.now)

    # Change target
    target: EvolutionTarget = Field(..., description="What to evolve")
    area: EvolutionArea = Field(..., description="Area of change")

    # Suggestion content
    suggestion: str = Field(..., description="Human-readable suggestion")
    current_value: Optional[Dict[str, Any]] = Field(
        None, description="Current value before change"
    )
    proposed_value: Optional[Dict[str, Any]] = Field(
        None, description="Proposed new value"
    )

    # Analysis
    rationale: str = Field(..., description="Why this change is recommended")
    expected_impact: str = Field(..., description="Expected effect of the change")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    severity: EvolutionSeverity = Field(
        default=EvolutionSeverity.MODERATE, description="Change severity"
    )

    # Evidence
    evidence: List[str] = Field(
        default_factory=list, description="Supporting data points"
    )
    source: EvolutionSource = Field(
        default=EvolutionSource.AUTOMATED, description="Source of suggestion"
    )

    # Status
    status: EvolutionSuggestionStatus = Field(
        default=EvolutionSuggestionStatus.PENDING, description="Current status"
    )
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    applied_version: Optional[str] = Field(
        None, description="Persona version after applying"
    )


class AgentConfig(BaseModel):
    """Per-persona agent configuration for customizing agent behavior"""

    agent_type: str = Field(..., description="Agent type: content, review, discovery")

    # LLM parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=8192)

    # Prompt customization
    system_prompt_additions: Optional[str] = Field(
        None, description="Additional system prompt text"
    )
    style_emphasis: List[str] = Field(
        default_factory=list, description="Styles to emphasize"
    )
    avoid_patterns: List[str] = Field(
        default_factory=list, description="Patterns to avoid"
    )

    # Behavior tuning
    creativity_level: str = Field(
        default="balanced",
        description="Creativity: conservative, balanced, creative",
    )
    detail_level: str = Field(
        default="standard",
        description="Detail level: brief, standard, detailed",
    )

    # Performance tracking
    performance_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Historical performance records"
    )


class EvolutionConfig(BaseModel):
    """Evolution configuration for a persona"""

    enabled: bool = Field(default=True, description="Whether evolution is enabled")

    # Auto-apply settings
    auto_apply_minor: bool = Field(
        default=True, description="Auto-apply minor changes"
    )
    auto_apply_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for auto-apply",
    )

    # Analysis triggers
    analysis_schedule: str = Field(
        default="weekly",
        description="Analysis frequency: daily, weekly, biweekly, monthly",
    )
    score_threshold: float = Field(
        default=65.0,
        description="Score below which to trigger analysis",
    )

    # Notification preferences
    notify_on_suggestion: bool = Field(
        default=True, description="Notify when suggestions are generated"
    )
    notify_on_auto_apply: bool = Field(
        default=True, description="Notify when changes are auto-applied"
    )


class EvolutionFeedbackAnalysis(BaseModel):
    """Analysis of feedback for evolution suggestions"""

    persona_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    period: str = Field(default="7d", description="Analysis period")

    # Review analysis
    review_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Review score patterns"
    )

    # Content performance
    content_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Content performance patterns"
    )

    # Discovery alignment
    discovery_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Discovery/trend alignment"
    )

    # Overall insights
    key_insights: List[str] = Field(
        default_factory=list, description="Key findings from analysis"
    )
    improvement_areas: List[str] = Field(
        default_factory=list, description="Areas needing improvement"
    )
    strengths: List[str] = Field(
        default_factory=list, description="Current strengths"
    )


# Rebuild Persona model to resolve forward references
Persona.model_rebuild()
