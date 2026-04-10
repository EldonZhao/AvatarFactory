"""
Evolution Agent - Manages Persona and Agent evolution.

Handles feedback analysis, suggestion generation, approval workflows,
and automatic evolution based on performance data.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from avatarfactory.agents.base import BaseAgent
from avatarfactory.core.agent_config import AgentConfigManager
from avatarfactory.models.schemas import (
    AgentConfig,
    AgentMessage,
    EvolutionArea,
    EvolutionConfig,
    EvolutionFeedbackAnalysis,
    EvolutionSeverity,
    EvolutionSource,
    EvolutionSuggestion,
    EvolutionSuggestionStatus,
    EvolutionTarget,
    Persona,
    PersonaVersion,
    TaskType,
)


class EvolutionAgent(BaseAgent):
    """Agent responsible for persona and sub-agent evolution"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="evolution", *args, **kwargs)
        self._config_manager: Optional[AgentConfigManager] = None

    @property
    def config_manager(self) -> AgentConfigManager:
        """Lazily initialize config manager."""
        if self._config_manager is None:
            self._config_manager = AgentConfigManager(self.kb)
        return self._config_manager

    async def process(self, message: AgentMessage) -> Any:
        """Process evolution-related tasks"""
        self.validate_message(message)

        # Route to appropriate handler based on task type
        task_type = message.task_type
        payload = message.payload
        context = message.context

        # Handle different evolution operations via payload action
        action = payload.get("action", "analyze")

        handlers = {
            "analyze": self._handle_analyze,
            "generate_suggestions": self._handle_generate_suggestions,
            "review_suggestion": self._handle_review_suggestion,
            "apply_suggestion": self._handle_apply_suggestion,
            "rollback": self._handle_rollback,
            "get_suggestions": self._handle_get_suggestions,
            "generate_retrospective": self._handle_generate_retrospective,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown evolution action: {action}")

        return await handler(payload, context)

    # =========================================================================
    # Feedback Analysis
    # =========================================================================

    async def analyze_feedback(
        self,
        persona_id: str,
        period: str = "7d",
    ) -> EvolutionFeedbackAnalysis:
        """
        Analyze feedback data for a persona.

        Collects review scores, content performance, and discovery insights
        to identify patterns and improvement areas.

        Args:
            persona_id: Persona ID
            period: Analysis period (e.g., "7d", "14d", "30d")

        Returns:
            EvolutionFeedbackAnalysis with patterns and insights
        """
        self.log("INFO", f"Analyzing feedback for {persona_id} over {period}")

        # Parse period
        days = self._parse_period(period)

        # Gather data from different sources
        review_analysis = await self._analyze_review_patterns(persona_id, days)
        content_analysis = await self._analyze_content_performance(persona_id, days)
        discovery_analysis = await self._analyze_discovery_alignment(persona_id)

        # Generate insights using LLM
        insights = await self._generate_insights(
            persona_id, review_analysis, content_analysis, discovery_analysis
        )

        # Create analysis object
        analysis = EvolutionFeedbackAnalysis(
            persona_id=persona_id,
            analyzed_at=datetime.now(),
            period=period,
            review_analysis=review_analysis,
            content_analysis=content_analysis,
            discovery_analysis=discovery_analysis,
            key_insights=insights.get("key_insights", []),
            improvement_areas=insights.get("improvement_areas", []),
            strengths=insights.get("strengths", []),
        )

        # Save analysis
        self.kb.save_feedback_analysis(persona_id, analysis)

        return analysis

    async def _analyze_review_patterns(
        self, persona_id: str, days: int
    ) -> Dict[str, Any]:
        """Analyze review score patterns."""
        cutoff = datetime.now() - timedelta(days=days)

        # Get content with review scores
        contents = self.kb.list_content(persona_id=persona_id, status="draft")
        contents += self.kb.list_content(persona_id=persona_id, status="published")

        # Filter by date
        recent_contents = [
            c for c in contents
            if c.created_at and c.created_at >= cutoff
        ]

        if not recent_contents:
            return {"sample_size": 0}

        # Calculate score statistics
        scores = [c.review_score for c in recent_contents if c.review_score]
        if not scores:
            return {"sample_size": len(recent_contents), "reviewed_count": 0}

        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)

        # Categorize issues
        all_issues = []
        for c in recent_contents:
            all_issues.extend(c.review_issues or [])

        # Count issue frequency
        issue_counts: Dict[str, int] = {}
        for issue in all_issues:
            # Normalize issue text
            key = issue.lower()[:50]
            issue_counts[key] = issue_counts.get(key, 0) + 1

        # Get top issues
        top_issues = sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "sample_size": len(recent_contents),
            "reviewed_count": len(scores),
            "avg_score": round(avg_score, 1),
            "min_score": min_score,
            "max_score": max_score,
            "score_trend": self._calculate_trend(
                [(c.created_at, c.review_score) for c in recent_contents if c.review_score]
            ),
            "top_issues": [{"issue": k, "count": v} for k, v in top_issues],
        }

    async def _analyze_content_performance(
        self, persona_id: str, days: int
    ) -> Dict[str, Any]:
        """Analyze content performance patterns."""
        cutoff = datetime.now() - timedelta(days=days)

        # Get published content
        published = self.kb.list_content(persona_id=persona_id, status="published")
        recent = [c for c in published if c.created_at and c.created_at >= cutoff]

        if not recent:
            return {"sample_size": 0}

        # Analyze by pillar
        pillar_stats: Dict[str, Dict[str, Any]] = {}
        for c in recent:
            pillar = c.pillar or "unknown"
            if pillar not in pillar_stats:
                pillar_stats[pillar] = {"count": 0, "scores": []}
            pillar_stats[pillar]["count"] += 1
            if c.review_score:
                pillar_stats[pillar]["scores"].append(c.review_score)

        # Calculate pillar averages
        for pillar, stats in pillar_stats.items():
            scores = stats["scores"]
            stats["avg_score"] = sum(scores) / len(scores) if scores else None
            del stats["scores"]  # Remove raw scores

        return {
            "sample_size": len(recent),
            "by_pillar": pillar_stats,
            "publishing_rate": len(recent) / max(days, 1),
        }

    async def _analyze_discovery_alignment(
        self, persona_id: str
    ) -> Dict[str, Any]:
        """Analyze how well persona aligns with discovered trends."""
        # Get latest discovery
        discovery = self.kb.get_latest_discovery(persona_id)
        if not discovery:
            return {"has_discovery": False}

        # Get persona
        persona = self.kb.load_persona(persona_id)
        if not persona:
            return {"has_discovery": True, "persona_found": False}

        # Check for persona suggestions from discovery
        suggestions = discovery.get("persona_suggestions", [])

        # Get trending topics
        ideas = discovery.get("ideas", [])
        trending_topics = []
        for idea in ideas[:10]:
            if isinstance(idea, dict):
                topic = idea.get("topic", "")
            else:
                topic = str(idea)
            if topic:
                trending_topics.append(topic)

        return {
            "has_discovery": True,
            "discovery_date": discovery.get("created_at"),
            "platform": discovery.get("platform"),
            "persona_suggestions_count": len(suggestions),
            "persona_suggestions": suggestions[:3],
            "trending_topics": trending_topics[:5],
        }

    async def _generate_insights(
        self,
        persona_id: str,
        review_analysis: Dict[str, Any],
        content_analysis: Dict[str, Any],
        discovery_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate insights from analysis using LLM."""
        persona = self.kb.load_persona(persona_id)
        if not persona:
            return {}

        system_prompt = """You are an expert in social media persona optimization.
Analyze the feedback data and provide actionable insights.

Output MUST be valid JSON:
{
    "key_insights": ["insight1", "insight2", ...],
    "improvement_areas": ["area1", "area2", ...],
    "strengths": ["strength1", "strength2", ...]
}

Keep each insight concise (1-2 sentences).
Focus on actionable, specific observations.
Limit to 3-5 items per category."""

        user_prompt = f"""Analyze this feedback data for persona "{persona.identity.name}":

REVIEW ANALYSIS:
{json.dumps(review_analysis, indent=2, ensure_ascii=False)}

CONTENT PERFORMANCE:
{json.dumps(content_analysis, indent=2, ensure_ascii=False)}

DISCOVERY ALIGNMENT:
{json.dumps(discovery_analysis, indent=2, ensure_ascii=False)}

PERSONA CONTEXT:
- Voice: {persona.voice_style.tone}
- Pillars: {[p.name for p in persona.content_pillars]}
- Target: {persona.target_audience.primary}

Provide insights in JSON format."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.4)

        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            self.log("WARNING", "Failed to parse insights response")
            return {
                "key_insights": [],
                "improvement_areas": [],
                "strengths": [],
            }

    # =========================================================================
    # Suggestion Generation
    # =========================================================================

    async def generate_suggestions(
        self,
        persona_id: str,
        analysis: Optional[EvolutionFeedbackAnalysis] = None,
        user_feedback: Optional[str] = None,
    ) -> List[EvolutionSuggestion]:
        """
        Generate evolution suggestions based on feedback analysis.

        Args:
            persona_id: Persona ID
            analysis: Feedback analysis (will fetch latest if not provided)
            user_feedback: Optional user feedback to incorporate

        Returns:
            List of EvolutionSuggestion
        """
        self.log("INFO", f"Generating suggestions for {persona_id}")

        # Get analysis if not provided
        if analysis is None:
            analysis = self.kb.load_feedback_analysis(persona_id)
            if analysis is None:
                # Run analysis first
                analysis = await self.analyze_feedback(persona_id)

        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        # Build context for LLM
        context = {
            "persona": {
                "name": persona.identity.name,
                "tagline": persona.identity.tagline,
                "voice_style": persona.voice_style.model_dump(),
                "content_pillars": [p.model_dump() for p in persona.content_pillars],
                "boundaries": persona.boundaries.model_dump(),
            },
            "analysis": {
                "key_insights": analysis.key_insights,
                "improvement_areas": analysis.improvement_areas,
                "review_stats": analysis.review_analysis,
            },
            "user_feedback": user_feedback,
        }

        suggestions = await self._generate_suggestions_with_llm(persona_id, context)

        # Save suggestions
        for suggestion in suggestions:
            self.kb.save_evolution_suggestion(persona_id, suggestion)

        return suggestions

    async def generate_suggestions_from_user_input(
        self,
        persona_id: str,
        user_input: str,
    ) -> List[EvolutionSuggestion]:
        """
        Generate evolution suggestions from direct user feedback.

        Args:
            persona_id: Persona ID
            user_input: User's feedback or suggestion

        Returns:
            List of EvolutionSuggestion
        """
        self.log("INFO", f"Generating suggestions from user input for {persona_id}")

        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        system_prompt = """You are an expert persona optimization assistant.
Based on user feedback, generate specific, actionable suggestions for improving the persona.

Output MUST be valid JSON array:
[
    {
        "target": "persona|content_agent|review_agent|topic_agent",
        "area": "identity|voice_style|content_pillars|boundaries|target_audience|agent_config",
        "suggestion": "Human-readable suggestion",
        "current_value": {"field": "current value"},
        "proposed_value": {"field": "new value"},
        "rationale": "Why this change is recommended",
        "expected_impact": "Expected effect of the change",
        "confidence": 0.0-1.0,
        "severity": "minor|moderate|major"
    }
]

Guidelines:
- Be specific about what to change
- Include both current and proposed values when applicable
- Set severity based on impact: minor (small tweak), moderate (noticeable change), major (significant shift)
- Set confidence based on clarity of user feedback"""

        user_prompt = f"""USER FEEDBACK:
{user_input}

CURRENT PERSONA:
- Name: {persona.identity.name}
- Tagline: {persona.identity.tagline}
- Voice Tone: {persona.voice_style.tone}
- Language Patterns: {persona.voice_style.language_patterns}
- Emoji Usage: {persona.voice_style.emoji_usage}
- Content Pillars: {[p.name for p in persona.content_pillars]}
- Boundaries to Avoid: {persona.boundaries.avoid}

Generate suggestions to address the user's feedback."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.5)

        try:
            json_str = self._extract_json(response)
            suggestions_data = json.loads(json_str)
        except json.JSONDecodeError:
            self.log("WARNING", "Failed to parse suggestions response")
            return []

        suggestions = []
        for data in suggestions_data:
            suggestion = EvolutionSuggestion(
                id=f"sug_{uuid.uuid4().hex[:8]}",
                created_at=datetime.now(),
                target=EvolutionTarget(data.get("target", "persona")),
                area=EvolutionArea(data.get("area", "voice_style")),
                suggestion=data.get("suggestion", ""),
                current_value=data.get("current_value"),
                proposed_value=data.get("proposed_value"),
                rationale=data.get("rationale", ""),
                expected_impact=data.get("expected_impact", ""),
                confidence=data.get("confidence", 0.5),
                severity=EvolutionSeverity(data.get("severity", "moderate")),
                evidence=[user_input],
                source=EvolutionSource.USER_FEEDBACK,
                status=EvolutionSuggestionStatus.PENDING,
            )
            suggestions.append(suggestion)
            self.kb.save_evolution_suggestion(persona_id, suggestion)

        return suggestions

    async def _generate_suggestions_with_llm(
        self, persona_id: str, context: Dict[str, Any]
    ) -> List[EvolutionSuggestion]:
        """Generate suggestions using LLM based on analysis context."""
        system_prompt = """You are an expert persona optimization assistant.
Based on the feedback analysis, generate specific, actionable suggestions.

Output MUST be valid JSON array:
[
    {
        "target": "persona|content_agent|review_agent|topic_agent",
        "area": "identity|voice_style|content_pillars|boundaries|target_audience|agent_config",
        "suggestion": "Human-readable suggestion",
        "current_value": {"field": "current value"},
        "proposed_value": {"field": "new value"},
        "rationale": "Why this change is recommended",
        "expected_impact": "Expected effect of the change",
        "confidence": 0.0-1.0,
        "severity": "minor|moderate|major"
    }
]

Guidelines:
- Focus on addressing the identified improvement areas
- Build on existing strengths
- Be specific about changes
- Provide 2-4 suggestions
- Set severity appropriately: minor (small tweaks), moderate (noticeable changes), major (significant shifts)"""

        user_prompt = f"""ANALYSIS CONTEXT:
{json.dumps(context, indent=2, ensure_ascii=False)}

Generate optimization suggestions."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.5)

        try:
            json_str = self._extract_json(response)
            suggestions_data = json.loads(json_str)
        except json.JSONDecodeError:
            self.log("WARNING", "Failed to parse suggestions response")
            return []

        suggestions = []
        for data in suggestions_data:
            suggestion = EvolutionSuggestion(
                id=f"sug_{uuid.uuid4().hex[:8]}",
                created_at=datetime.now(),
                target=EvolutionTarget(data.get("target", "persona")),
                area=EvolutionArea(data.get("area", "voice_style")),
                suggestion=data.get("suggestion", ""),
                current_value=data.get("current_value"),
                proposed_value=data.get("proposed_value"),
                rationale=data.get("rationale", ""),
                expected_impact=data.get("expected_impact", ""),
                confidence=data.get("confidence", 0.5),
                severity=EvolutionSeverity(data.get("severity", "moderate")),
                evidence=context.get("analysis", {}).get("key_insights", []),
                source=EvolutionSource.AUTOMATED,
                status=EvolutionSuggestionStatus.PENDING,
            )
            suggestions.append(suggestion)

        return suggestions

    # =========================================================================
    # Approval Workflow
    # =========================================================================

    async def review_suggestion(
        self,
        persona_id: str,
        suggestion_id: str,
        approved: bool,
        rejection_reason: Optional[str] = None,
    ) -> EvolutionSuggestion:
        """
        Review and approve/reject an evolution suggestion.

        Args:
            persona_id: Persona ID
            suggestion_id: Suggestion ID
            approved: Whether to approve the suggestion
            rejection_reason: Reason for rejection (if rejected)

        Returns:
            Updated EvolutionSuggestion
        """
        self.log(
            "INFO",
            f"Reviewing suggestion {suggestion_id}: {'approved' if approved else 'rejected'}"
        )

        suggestion = self.kb.load_evolution_suggestion(persona_id, suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")

        if suggestion.status != EvolutionSuggestionStatus.PENDING:
            raise ValueError(f"Suggestion already reviewed: {suggestion.status}")

        # Update status
        suggestion.reviewed_at = datetime.now()

        if approved:
            suggestion.status = EvolutionSuggestionStatus.APPROVED
            # Apply the suggestion
            await self.apply_suggestion(persona_id, suggestion)
        else:
            suggestion.status = EvolutionSuggestionStatus.REJECTED
            suggestion.rejection_reason = rejection_reason

        # Save updated suggestion
        self.kb.save_evolution_suggestion(persona_id, suggestion)

        return suggestion

    async def apply_suggestion(
        self,
        persona_id: str,
        suggestion: EvolutionSuggestion,
        auto_applied: bool = False,
    ) -> Dict[str, Any]:
        """
        Apply an approved evolution suggestion.

        Args:
            persona_id: Persona ID
            suggestion: Suggestion to apply
            auto_applied: Whether this was auto-applied

        Returns:
            Dict with old and new values
        """
        self.log("INFO", f"Applying suggestion {suggestion.id} to {persona_id}")

        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        result = {
            "suggestion_id": suggestion.id,
            "target": suggestion.target.value,
            "area": suggestion.area.value,
            "auto_applied": auto_applied,
        }

        # Apply based on target
        if suggestion.target == EvolutionTarget.PERSONA:
            result.update(
                await self._apply_persona_change(persona, suggestion)
            )
        else:
            # Agent config change
            result.update(
                await self._apply_agent_config_change(persona_id, suggestion)
            )

        # Update suggestion status
        if auto_applied:
            suggestion.status = EvolutionSuggestionStatus.AUTO_APPLIED
        else:
            suggestion.status = EvolutionSuggestionStatus.APPROVED
        suggestion.applied_version = result.get("new_version")
        self.kb.save_evolution_suggestion(persona_id, suggestion)

        return result

    async def _apply_persona_change(
        self,
        persona: Persona,
        suggestion: EvolutionSuggestion,
    ) -> Dict[str, Any]:
        """Apply a change to persona configuration."""
        old_version = persona.version
        proposed = suggestion.proposed_value or {}

        # Apply changes based on area
        if suggestion.area == EvolutionArea.VOICE_STYLE:
            for key, value in proposed.items():
                if hasattr(persona.voice_style, key):
                    setattr(persona.voice_style, key, value)

        elif suggestion.area == EvolutionArea.IDENTITY:
            for key, value in proposed.items():
                if hasattr(persona.identity, key):
                    setattr(persona.identity, key, value)

        elif suggestion.area == EvolutionArea.BOUNDARIES:
            for key, value in proposed.items():
                if hasattr(persona.boundaries, key):
                    setattr(persona.boundaries, key, value)

        elif suggestion.area == EvolutionArea.TARGET_AUDIENCE:
            for key, value in proposed.items():
                if hasattr(persona.target_audience, key):
                    setattr(persona.target_audience, key, value)

        elif suggestion.area == EvolutionArea.CONTENT_PILLARS:
            # Handle pillar changes (more complex)
            if "add_pillar" in proposed:
                from avatarfactory.models.schemas import ContentPillar
                new_pillar = ContentPillar(**proposed["add_pillar"])
                persona.content_pillars.append(new_pillar)
            if "remove_pillar" in proposed:
                persona.content_pillars = [
                    p for p in persona.content_pillars
                    if p.name != proposed["remove_pillar"]
                ]
            if "update_pillar" in proposed:
                for p in persona.content_pillars:
                    if p.name == proposed["update_pillar"].get("name"):
                        for key, value in proposed["update_pillar"].items():
                            if hasattr(p, key):
                                setattr(p, key, value)

        # Increment version
        new_version = self._increment_version(old_version, suggestion.severity)
        persona.version = new_version
        persona.updated_at = datetime.now()

        # Save persona
        self.kb.save_persona(persona)

        # Save version record
        version_record = PersonaVersion(
            version=new_version,
            timestamp=datetime.now(),
            changes=[suggestion.suggestion],
            reason=suggestion.rationale,
            expected_impact=suggestion.expected_impact,
            author="evolution_agent",
            approved=True,
        )
        self.kb.save_persona_version(persona.id, version_record)

        return {
            "old_version": old_version,
            "new_version": new_version,
        }

    async def _apply_agent_config_change(
        self,
        persona_id: str,
        suggestion: EvolutionSuggestion,
    ) -> Dict[str, Any]:
        """Apply a change to agent configuration."""
        # Determine agent type
        agent_type_map = {
            EvolutionTarget.CONTENT_AGENT: "content",
            EvolutionTarget.REVIEW_AGENT: "review",
            EvolutionTarget.TOPIC_AGENT: "topic",
        }
        agent_type = agent_type_map.get(suggestion.target, "content")

        # Get current config
        old_config = self.config_manager.get_config(persona_id, agent_type)
        old_dict = old_config.model_dump()

        # Apply proposed changes
        proposed = suggestion.proposed_value or {}
        new_config = self.config_manager.update_config(
            persona_id, agent_type, proposed
        )

        return {
            "agent_type": agent_type,
            "old_config": old_dict,
            "new_config": new_config.model_dump(),
        }

    async def rollback_change(
        self,
        persona_id: str,
        version: str,
    ) -> Persona:
        """
        Rollback persona to a previous version.

        Args:
            persona_id: Persona ID
            version: Version to rollback to

        Returns:
            Restored Persona
        """
        self.log("INFO", f"Rolling back {persona_id} to {version}")

        # Load the target version
        old_persona = self.kb.get_persona_version(persona_id, version)
        if not old_persona:
            raise ValueError(f"Version {version} not found for {persona_id}")

        # Get current version
        current = self.kb.load_persona(persona_id)
        current_version = current.version if current else "unknown"

        # Create new version for the rollback
        new_version = self._increment_version(current_version, EvolutionSeverity.MAJOR)

        # Update metadata
        old_persona.version = new_version
        old_persona.updated_at = datetime.now()

        # Save
        self.kb.save_persona(old_persona)

        # Record version
        version_record = PersonaVersion(
            version=new_version,
            timestamp=datetime.now(),
            changes=[f"Rollback to {version}"],
            reason="User-requested rollback",
            expected_impact="Restore previous behavior",
            author="evolution_agent",
            approved=True,
        )
        self.kb.save_persona_version(persona_id, version_record)

        return old_persona

    # =========================================================================
    # Auto Evolution
    # =========================================================================

    async def check_auto_evolution_triggers(
        self, persona_id: str
    ) -> bool:
        """
        Check if auto-evolution should be triggered.

        Args:
            persona_id: Persona ID

        Returns:
            True if auto-evolution conditions are met
        """
        persona = self.kb.load_persona(persona_id)
        if not persona:
            return False

        # Check if evolution is enabled
        evolution_config = persona.evolution
        if not evolution_config or not evolution_config.enabled:
            return False

        # Get latest analysis
        analysis = self.kb.load_feedback_analysis(persona_id)
        if not analysis:
            return True  # No analysis yet, should run one

        # Check if analysis is stale
        schedule_days = {
            "daily": 1,
            "weekly": 7,
            "biweekly": 14,
            "monthly": 30,
        }
        max_age_days = schedule_days.get(
            evolution_config.analysis_schedule, 7
        )
        age = datetime.now() - analysis.analyzed_at
        if age.days >= max_age_days:
            return True

        # Check if scores are below threshold
        if analysis.review_analysis:
            avg_score = analysis.review_analysis.get("avg_score")
            if avg_score and avg_score < evolution_config.score_threshold:
                return True

        return False

    async def run_scheduled_evolution(
        self, persona_id: str
    ) -> Dict[str, Any]:
        """
        Run scheduled evolution analysis and suggestion generation.

        Args:
            persona_id: Persona ID

        Returns:
            Dict with analysis and suggestions
        """
        self.log("INFO", f"Running scheduled evolution for {persona_id}")

        # Run analysis
        analysis = await self.analyze_feedback(persona_id)

        # Generate suggestions
        suggestions = await self.generate_suggestions(persona_id, analysis)

        # Check for auto-apply
        persona = self.kb.load_persona(persona_id)
        evolution_config = persona.evolution if persona else None

        auto_applied = []
        if evolution_config and evolution_config.auto_apply_minor:
            for suggestion in suggestions:
                if (
                    suggestion.severity == EvolutionSeverity.MINOR
                    and suggestion.confidence >= evolution_config.auto_apply_threshold
                ):
                    await self.apply_suggestion(persona_id, suggestion, auto_applied=True)
                    auto_applied.append(suggestion.id)

        return {
            "analysis": analysis.model_dump(mode="json"),
            "suggestions_count": len(suggestions),
            "auto_applied_count": len(auto_applied),
            "auto_applied_ids": auto_applied,
            "pending_approval": [
                s.id for s in suggestions
                if s.status == EvolutionSuggestionStatus.PENDING
            ],
        }

    # =========================================================================
    # Retrospective Generation
    # =========================================================================

    async def generate_retrospective(
        self,
        persona_id: str,
        period: str = "weekly",
    ) -> Dict[str, Any]:
        """
        Generate a retrospective report for a persona.

        Args:
            persona_id: Persona ID
            period: Retrospective period (weekly, biweekly, monthly)

        Returns:
            Dict with retrospective data
        """
        self.log("INFO", f"Generating {period} retrospective for {persona_id}")

        # Get period in days
        period_days = {"weekly": 7, "biweekly": 14, "monthly": 30}.get(period, 7)

        # Run fresh analysis
        analysis = await self.analyze_feedback(persona_id, f"{period_days}d")

        # Get persona history
        history = self.kb.get_persona_history(persona_id)
        recent_versions = [
            v for v in history
            if v.timestamp >= datetime.now() - timedelta(days=period_days)
        ]

        # Get evolution suggestions history
        all_suggestions = self.kb.list_evolution_suggestions(persona_id)
        recent_suggestions = [
            s for s in all_suggestions
            if s.created_at >= datetime.now() - timedelta(days=period_days)
        ]

        # Generate retrospective using LLM
        retro_data = await self._generate_retrospective_content(
            persona_id, analysis, recent_versions, recent_suggestions
        )

        # Create week identifier
        week = datetime.now().strftime("%Y-W%W")

        from avatarfactory.models.schemas import WeeklyRetrospective
        retrospective = WeeklyRetrospective(
            week=week,
            persona_id=persona_id,
            generated_at=datetime.now(),
            summary=retro_data.get("summary", {}),
            what_worked=retro_data.get("what_worked", []),
            what_didnt=retro_data.get("what_didnt", []),
            key_insights=retro_data.get("key_insights", []),
            next_week_plan=retro_data.get("next_week_plan", {}),
        )

        # Save retrospective
        self.kb.save_retrospective(retrospective)

        return retrospective.model_dump(mode="json")

    async def _generate_retrospective_content(
        self,
        persona_id: str,
        analysis: EvolutionFeedbackAnalysis,
        recent_versions: List[PersonaVersion],
        recent_suggestions: List[EvolutionSuggestion],
    ) -> Dict[str, Any]:
        """Generate retrospective content using LLM."""
        persona = self.kb.load_persona(persona_id)
        if not persona:
            return {}

        system_prompt = """You are a content strategy analyst.
Generate a weekly retrospective report for a social media persona.

Output MUST be valid JSON:
{
    "summary": {
        "content_generated": <count>,
        "avg_score": <score>,
        "evolution_changes": <count>
    },
    "what_worked": ["thing1", "thing2"],
    "what_didnt": ["thing1", "thing2"],
    "key_insights": ["insight1", "insight2"],
    "next_week_plan": {
        "focus_areas": ["area1", "area2"],
        "goals": ["goal1", "goal2"]
    }
}"""

        context = {
            "persona_name": persona.identity.name,
            "analysis": {
                "review_stats": analysis.review_analysis,
                "content_stats": analysis.content_analysis,
                "insights": analysis.key_insights,
            },
            "persona_changes": [v.model_dump(mode="json") for v in recent_versions],
            "evolution_suggestions": len(recent_suggestions),
        }

        user_prompt = f"""Generate retrospective for:
{json.dumps(context, indent=2, ensure_ascii=False)}"""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.4)

        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}

    # =========================================================================
    # Handler Methods
    # =========================================================================

    async def _handle_analyze(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle analyze action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        if not persona_id:
            raise ValueError("persona_id required")

        period = payload.get("period", "7d")
        analysis = await self.analyze_feedback(persona_id, period)
        return {"analysis": analysis.model_dump(mode="json")}

    async def _handle_generate_suggestions(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle generate_suggestions action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        if not persona_id:
            raise ValueError("persona_id required")

        user_feedback = payload.get("user_feedback")

        if user_feedback:
            suggestions = await self.generate_suggestions_from_user_input(
                persona_id, user_feedback
            )
        else:
            suggestions = await self.generate_suggestions(persona_id)

        return {
            "suggestions": [s.model_dump(mode="json") for s in suggestions],
            "count": len(suggestions),
        }

    async def _handle_review_suggestion(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle review_suggestion action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        suggestion_id = payload.get("suggestion_id")
        approved = payload.get("approved", False)
        rejection_reason = payload.get("rejection_reason")

        if not persona_id or not suggestion_id:
            raise ValueError("persona_id and suggestion_id required")

        suggestion = await self.review_suggestion(
            persona_id, suggestion_id, approved, rejection_reason
        )
        return {"suggestion": suggestion.model_dump(mode="json")}

    async def _handle_apply_suggestion(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle apply_suggestion action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        suggestion_id = payload.get("suggestion_id")

        if not persona_id or not suggestion_id:
            raise ValueError("persona_id and suggestion_id required")

        suggestion = self.kb.load_evolution_suggestion(persona_id, suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")

        result = await self.apply_suggestion(persona_id, suggestion)
        return result

    async def _handle_rollback(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle rollback action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        version = payload.get("version")

        if not persona_id or not version:
            raise ValueError("persona_id and version required")

        persona = await self.rollback_change(persona_id, version)
        return {"persona": persona.model_dump(mode="json")}

    async def _handle_get_suggestions(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_suggestions action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        if not persona_id:
            raise ValueError("persona_id required")

        status = payload.get("status")
        suggestions = self.kb.list_evolution_suggestions(persona_id, status)

        return {
            "suggestions": [s.model_dump(mode="json") for s in suggestions],
            "count": len(suggestions),
        }

    async def _handle_generate_retrospective(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle generate_retrospective action."""
        persona_id = payload.get("persona_id") or context.get("persona_id")
        if not persona_id:
            raise ValueError("persona_id required")

        period = payload.get("period", "weekly")
        retrospective = await self.generate_retrospective(persona_id, period)
        return {"retrospective": retrospective}

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _parse_period(self, period: str) -> int:
        """Parse period string to days."""
        if period.endswith("d"):
            return int(period[:-1])
        elif period.endswith("w"):
            return int(period[:-1]) * 7
        else:
            return 7  # Default to 7 days

    def _calculate_trend(
        self, data_points: List[Tuple[datetime, float]]
    ) -> str:
        """Calculate trend from time series data."""
        if len(data_points) < 2:
            return "stable"

        # Sort by date
        sorted_points = sorted(data_points, key=lambda x: x[0])

        # Compare first half vs second half
        mid = len(sorted_points) // 2
        first_half = [p[1] for p in sorted_points[:mid]]
        second_half = [p[1] for p in sorted_points[mid:]]

        if not first_half or not second_half:
            return "stable"

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        diff = second_avg - first_avg
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"

    def _increment_version(
        self, current_version: str, severity: EvolutionSeverity
    ) -> str:
        """Increment version based on change severity."""
        parts = current_version.lstrip("v").split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0

        if severity == EvolutionSeverity.MAJOR:
            major += 1
            minor = 0
        else:
            minor += 1

        return f"v{major}.{minor}"

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response."""
        json_str = text.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        return json_str.strip()
