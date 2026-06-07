"""
Database-backed KnowledgeBase implementation.

This module provides a database-backed version of KnowledgeBase that uses
SQLAlchemy repositories for data access while maintaining API compatibility.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from avatarfactory.core.database.connection import get_session, init_database
from avatarfactory.core.database.models import (
    PersonaModel,
    PersonaVersionModel,
    ContentModel,
    ReviewModel,
    SimulationModel,
    DiscoveryResultModel,
    EvolutionSuggestionModel,
    TrendSnapshotModel,
    RecommendedPersonaModel,
)
from avatarfactory.core.database.repositories.persona import PersonaRepository
from avatarfactory.core.database.repositories.content import ContentRepository, ReviewRepository
from avatarfactory.core.database.repositories.scheduler import (
    TrendSnapshotRepository,
    RecommendedPersonaRepository,
)
from avatarfactory.models.schemas import (
    Content,
    Persona,
    PersonaVersion,
    ReviewReport,
    SimulationReport,
    RecommendedPersona,
    TrendSnapshot,
    EvolutionSuggestion,
    Experiment,
    WeeklyRetrospective,
    EvolutionFeedbackAnalysis,
    AgentConfig,
)


def _run_async(coro):
    """Run async function in sync context."""
    try:
        asyncio.get_running_loop()
        # We're in an async context, create a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop, we can use asyncio.run
        return asyncio.run(coro)


class KnowledgeBaseDB:
    """
    Database-backed KnowledgeBase implementation.

    Provides the same API as KnowledgeBase but uses SQLAlchemy repositories
    for data access instead of file-based storage.
    """

    def __init__(self, base_path: str = "./knowledges"):
        """
        Initialize database-backed KnowledgeBase.

        Args:
            base_path: Base path for the database file (SQLite) or legacy files
        """
        self.base_path = Path(base_path)
        self._initialized = False
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database is initialized."""
        if not self._initialized:
            _run_async(init_database(kb_path=str(self.base_path)))
            self._initialized = True

    # ========================================================================
    # Persona Management
    # ========================================================================

    def save_persona(self, persona: Persona) -> None:
        """Save or update a persona."""
        async def _save():
            async with get_session() as session:
                repo = PersonaRepository(session)

                # Check if exists
                existing = await repo.get(persona.id)

                identity = persona.identity.model_dump() if persona.identity else {}

                if existing:
                    # Update existing
                    existing.version = persona.version
                    existing.name = identity.get("name", persona.id)
                    existing.tagline = identity.get("tagline")
                    existing.expertise = identity.get("expertise")
                    existing.identity = identity
                    existing.target_audience = persona.target_audience.model_dump() if persona.target_audience else {}
                    existing.voice_style = persona.voice_style.model_dump() if persona.voice_style else {}
                    existing.content_pillars = persona.content_pillars.model_dump() if persona.content_pillars else {}
                    existing.boundaries = persona.boundaries.model_dump() if persona.boundaries else {}
                    existing.notification = persona.notification.model_dump() if persona.notification else None
                    existing.evolution = persona.evolution.model_dump() if persona.evolution else None
                    existing.agent_configs = persona.agent_configs
                    existing.metadata_ = persona.metadata
                    existing.updated_at = datetime.utcnow()
                    await session.flush()
                else:
                    # Create new
                    model = PersonaModel(
                        id=persona.id,
                        version=persona.version,
                        name=identity.get("name", persona.id),
                        tagline=identity.get("tagline"),
                        expertise=identity.get("expertise"),
                        identity=identity,
                        target_audience=persona.target_audience.model_dump() if persona.target_audience else {},
                        voice_style=persona.voice_style.model_dump() if persona.voice_style else {},
                        content_pillars=persona.content_pillars.model_dump() if persona.content_pillars else {},
                        boundaries=persona.boundaries.model_dump() if persona.boundaries else {},
                        notification=persona.notification.model_dump() if persona.notification else None,
                        evolution=persona.evolution.model_dump() if persona.evolution else None,
                        agent_configs=persona.agent_configs,
                        metadata_=persona.metadata,
                    )
                    await repo.save(model)

        _run_async(_save())

    def load_persona(self, persona_id: str) -> Optional[Persona]:
        """Load a persona by ID."""
        async def _load():
            async with get_session() as session:
                repo = PersonaRepository(session)
                model = await repo.get(persona_id)
                if model and not model.is_deleted:
                    return repo.to_schema(model)
                return None

        return _run_async(_load())

    def list_personas(self, sort_by_created: bool = True) -> List[str]:
        """List all persona IDs."""
        async def _list():
            async with get_session() as session:
                repo = PersonaRepository(session)
                personas = await repo.list_active()
                return [p.id for p in personas]

        return _run_async(_list())

    def save_persona_version(self, persona_id: str, version_info: PersonaVersion) -> None:
        """Save persona version history record."""
        async def _save():
            async with get_session() as session:
                repo = PersonaRepository(session)
                await repo.save_version(
                    persona_id=persona_id,
                    version=version_info.version,
                    changes=version_info.changes,
                    reason=version_info.reason,
                    expected_impact=version_info.expected_impact,
                    config_snapshot=version_info.config_snapshot or {},
                    author=version_info.author,
                )

        _run_async(_save())

    def get_persona_history(self, persona_id: str) -> List[PersonaVersion]:
        """Get persona version history."""
        async def _get():
            async with get_session() as session:
                repo = PersonaRepository(session)
                versions = await repo.get_versions(persona_id)
                return [
                    PersonaVersion(
                        version=v.version,
                        changes=v.changes,
                        reason=v.reason,
                        expected_impact=v.expected_impact,
                        timestamp=v.timestamp,
                        author=v.author,
                        approved=v.approved,
                        config_snapshot=v.config_snapshot,
                    )
                    for v in versions
                ]

        return _run_async(_get())

    def delete_persona(self, persona_id: str, delete_content: bool = True) -> Dict[str, Any]:
        """Delete a persona (soft delete)."""
        async def _delete():
            result = {
                "persona_deleted": False,
                "content_deleted": 0,
                "discovery_deleted": 0,
                "errors": [],
            }

            async with get_session() as session:
                repo = PersonaRepository(session)

                # Count content before deletion
                if delete_content:
                    content_repo = ContentRepository(session)
                    contents = await content_repo.list_by_persona(persona_id)
                    result["content_deleted"] = len(contents)

                # Soft delete persona (cascades to related data)
                success = await repo.soft_delete(persona_id)
                result["persona_deleted"] = success

                if not success:
                    result["errors"].append(f"Persona {persona_id} not found")

            return result

        return _run_async(_delete())

    # ========================================================================
    # Content Management
    # ========================================================================

    def save_content(self, content: Content, status: str = "draft") -> None:
        """Save content."""
        async def _save():
            async with get_session() as session:
                repo = ContentRepository(session)

                existing = await repo.get(content.id)

                if existing:
                    # Update existing
                    existing.title = content.title or ""
                    existing.body = content.body
                    existing.pillar = content.pillar or ""
                    existing.platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
                    existing.content_type = content.content_type.value if hasattr(content.content_type, 'value') else str(content.content_type)
                    existing.status = status
                    existing.tags = content.tags
                    existing.media = [m.model_dump() for m in content.media] if content.media else None
                    existing.image_prompts = content.image_prompts
                    existing.metadata_ = content.metadata
                    if status == "published":
                        existing.published_at = datetime.utcnow()
                    await session.flush()
                else:
                    # Create new
                    model = ContentModel(
                        id=content.id,
                        persona_id=content.persona_id,
                        created_at=content.created_at,
                        title=content.title or "",
                        body=content.body,
                        pillar=content.pillar or "",
                        platform=content.platform.value if hasattr(content.platform, 'value') else str(content.platform),
                        content_type=content.content_type.value if hasattr(content.content_type, 'value') else str(content.content_type),
                        status=status,
                        published_at=datetime.utcnow() if status == "published" else None,
                        structure=content.structure.model_dump() if content.structure else None,
                        tags=content.tags,
                        media=[m.model_dump() for m in content.media] if content.media else None,
                        image_prompts=content.image_prompts,
                        metadata_=content.metadata,
                    )
                    await repo.save(model)

        _run_async(_save())

    def load_content(self, content_id: str, status: str = "draft") -> Optional[Content]:
        """Load content by ID."""
        async def _load():
            async with get_session() as session:
                repo = ContentRepository(session)
                model = await repo.get(content_id)
                if model:
                    return self._model_to_content(model)
                return None

        return _run_async(_load())

    def _model_to_content(self, model: ContentModel) -> Content:
        """Convert ContentModel to Content schema."""
        from avatarfactory.models.schemas import PlatformType, ContentType, ContentStructure, MediaAttachment

        platform = PlatformType(model.platform) if model.platform else PlatformType.BLUESKY
        content_type = ContentType(model.content_type) if model.content_type else ContentType.TEXT

        return Content(
            id=model.id,
            persona_id=model.persona_id,
            created_at=model.created_at,
            title=model.title,
            body=model.body,
            pillar=model.pillar,
            platform=platform,
            content_type=content_type,
            structure=ContentStructure(**model.structure) if model.structure else None,
            tags=model.tags or [],
            media=[MediaAttachment(**m) for m in model.media] if model.media else [],
            image_prompts=model.image_prompts or [],
            metadata=model.metadata_ or {},
        )

    def list_content(
        self, persona_id: Optional[str] = None, status: str = "draft"
    ) -> List[Content]:
        """List content, optionally filtered by persona_id."""
        async def _list():
            async with get_session() as session:
                repo = ContentRepository(session)

                if persona_id:
                    models = await repo.list_by_persona(persona_id, status=status)
                else:
                    models = await repo.list_with_reviews(status=status)

                return [self._model_to_content(m) for m in models]

        return _run_async(_list())

    def move_to_published(self, content_id: str) -> bool:
        """Move content from draft to published."""
        async def _move():
            async with get_session() as session:
                repo = ContentRepository(session)
                return await repo.publish(content_id)

        return _run_async(_move())

    def delete_content(self, content_id: str, status: str = "draft") -> bool:
        """Delete content by ID."""
        async def _delete():
            async with get_session() as session:
                repo = ContentRepository(session)
                return await repo.delete(content_id)

        return _run_async(_delete())

    # ========================================================================
    # Review Reports
    # ========================================================================

    def save_review_report(self, report: ReviewReport, persona_id: str) -> None:
        """Save review report."""
        async def _save():
            async with get_session() as session:
                review_repo = ReviewRepository(session)
                content_repo = ContentRepository(session)

                # Check if review exists
                existing = await review_repo.get_by_content(report.content_id)

                review_data = {
                    "content_id": report.content_id,
                    "reviewed_at": report.reviewed_at or datetime.utcnow(),
                    "persona_consistency_score": report.persona_consistency.score if report.persona_consistency else 0,
                    "platform_fit_score": report.platform_fit.score if report.platform_fit else 0,
                    "compliance_score": report.compliance.score if report.compliance else 0,
                    "engagement_potential_score": report.engagement_potential.score if report.engagement_potential else 0,
                    "overall_score": report.overall_score,
                    "persona_consistency": report.persona_consistency.model_dump() if report.persona_consistency else {},
                    "platform_fit": report.platform_fit.model_dump() if report.platform_fit else {},
                    "compliance": report.compliance.model_dump() if report.compliance else {},
                    "engagement_potential": report.engagement_potential.model_dump() if report.engagement_potential else {},
                    "suggestions": [s.model_dump() for s in report.suggestions] if report.suggestions else None,
                }

                if existing:
                    for key, value in review_data.items():
                        if key != "content_id":
                            setattr(existing, key, value)
                    await session.flush()
                else:
                    model = ReviewModel(**review_data)
                    session.add(model)
                    await session.flush()

                # Update denormalized score on content
                await content_repo.update_review_score(
                    report.content_id,
                    report.overall_score,
                    [s.suggestion for s in report.suggestions] if report.suggestions else None
                )

        _run_async(_save())

    def load_review_report(
        self, content_id: str, persona_id: str
    ) -> Optional[ReviewReport]:
        """Load review report."""
        async def _load():
            async with get_session() as session:
                repo = ReviewRepository(session)
                model = await repo.get_by_content(content_id)
                if not model:
                    return None

                from avatarfactory.models.schemas import ReviewDimension, ReviewSuggestion

                return ReviewReport(
                    content_id=model.content_id,
                    reviewed_at=model.reviewed_at,
                    overall_score=model.overall_score,
                    persona_consistency=ReviewDimension(**model.persona_consistency) if model.persona_consistency else None,
                    platform_fit=ReviewDimension(**model.platform_fit) if model.platform_fit else None,
                    compliance=ReviewDimension(**model.compliance) if model.compliance else None,
                    engagement_potential=ReviewDimension(**model.engagement_potential) if model.engagement_potential else None,
                    suggestions=[ReviewSuggestion(**s) for s in model.suggestions] if model.suggestions else None,
                )

        return _run_async(_load())

    # ========================================================================
    # Discovery Results
    # ========================================================================

    def save_discovery_results(
        self,
        persona_id: str,
        platform: str,
        results: Dict[str, Any],
    ) -> str:
        """Save discovery/trending results for a persona."""
        async def _save():
            async with get_session() as session:
                ideas = results.get("ideas", [])
                model = DiscoveryResultModel(
                    persona_id=persona_id,
                    platform=platform,
                    created_at=datetime.utcnow(),
                    trending_count=len(results.get("trending_posts", [])),
                    ideas_count=len(ideas),
                    pattern_analysis=results.get("pattern_analysis"),
                    ideas=ideas,
                    persona_suggestions=results.get("persona_suggestions"),
                    raw_data=results.get("raw_data"),
                )
                session.add(model)
                await session.flush()
                return f"discovery_{model.id}"

        return _run_async(_save())

    def get_latest_discovery(
        self,
        persona_id: str,
        platform: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get latest discovery results for a persona."""
        async def _get():
            async with get_session() as session:
                from sqlalchemy import select

                query = (
                    select(DiscoveryResultModel)
                    .where(DiscoveryResultModel.persona_id == persona_id)
                    .order_by(DiscoveryResultModel.created_at.desc())
                    .limit(1)
                )

                if platform:
                    query = query.where(DiscoveryResultModel.platform == platform)

                result = await session.execute(query)
                model = result.scalar_one_or_none()

                if not model:
                    return None

                return {
                    "platform": model.platform,
                    "created_at": model.created_at.isoformat(),
                    "trending_count": model.trending_count,
                    "ideas_count": model.ideas_count,
                    "pattern_analysis": model.pattern_analysis,
                    "ideas": model.ideas,
                    "persona_suggestions": model.persona_suggestions,
                }

        return _run_async(_get())

    def list_discovery_history(
        self,
        persona_id: str,
        platform: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List discovery history for a persona."""
        async def _list():
            async with get_session() as session:
                from sqlalchemy import select

                query = (
                    select(DiscoveryResultModel)
                    .where(DiscoveryResultModel.persona_id == persona_id)
                    .order_by(DiscoveryResultModel.created_at.desc())
                    .limit(limit)
                )

                if platform:
                    query = query.where(DiscoveryResultModel.platform == platform)

                result = await session.execute(query)
                models = result.scalars().all()

                return [
                    {
                        "platform": m.platform,
                        "created_at": m.created_at.isoformat(),
                        "trending_count": m.trending_count,
                        "ideas_count": m.ideas_count,
                        "pattern_analysis": m.pattern_analysis,
                        "ideas": m.ideas,
                    }
                    for m in models
                ]

        return _run_async(_list())

    # ========================================================================
    # Recommended Personas
    # ========================================================================

    def save_recommended_personas(
        self,
        personas: List[RecommendedPersona],
        date: Optional[str] = None,
    ) -> str:
        """Save recommended personas."""
        async def _save():
            async with get_session() as session:
                repo = RecommendedPersonaRepository(session)

                for p in personas:
                    model = RecommendedPersonaModel(
                        id=p.id,
                        created_at=p.created_at or datetime.utcnow(),
                        source_platforms=p.source_platforms,
                        source_trends=p.source_trends,
                        name=p.name,
                        tagline=p.tagline,
                        domain=p.domain,
                        expertise=p.expertise,
                        target_audience=p.target_audience,
                        audience_pain_points=p.audience_pain_points,
                        suggested_tone=p.suggested_tone,
                        content_types=p.content_types,
                        content_pillars=p.content_pillars,
                        relevance_score=p.relevance_score,
                        potential_score=p.potential_score,
                        rationale=p.rationale,
                        status=p.status.value if hasattr(p.status, 'value') else str(p.status),
                    )
                    await repo.save(model)

                return f"recommendations_{date or datetime.now().strftime('%Y-%m-%d')}"

        return _run_async(_save())

    def get_recommended_personas(
        self,
        limit: int = 10,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[RecommendedPersona]:
        """Get recommended personas."""
        async def _get():
            async with get_session() as session:
                repo = RecommendedPersonaRepository(session)

                if status == "active":
                    models = await repo.list_active(limit=limit)
                else:
                    models = await repo.list(limit=limit, order_by="-created_at")

                results = []
                for m in models:
                    if domain and m.domain.lower() != domain.lower():
                        continue

                    from avatarfactory.models.schemas import RecommendationStatus

                    results.append(RecommendedPersona(
                        id=m.id,
                        created_at=m.created_at,
                        source_platforms=m.source_platforms,
                        source_trends=m.source_trends,
                        name=m.name,
                        tagline=m.tagline,
                        domain=m.domain,
                        expertise=m.expertise,
                        target_audience=m.target_audience,
                        audience_pain_points=m.audience_pain_points,
                        suggested_tone=m.suggested_tone,
                        content_types=m.content_types,
                        content_pillars=m.content_pillars,
                        relevance_score=m.relevance_score,
                        potential_score=m.potential_score,
                        rationale=m.rationale,
                        status=RecommendationStatus(m.status) if m.status else RecommendationStatus.ACTIVE,
                        adopted_persona_id=m.adopted_persona_id,
                    ))

                return results[:limit]

        return _run_async(_get())

    def get_recommendation(self, rec_id: str) -> Optional[RecommendedPersona]:
        """Get a specific recommendation by ID."""
        async def _get():
            async with get_session() as session:
                repo = RecommendedPersonaRepository(session)
                model = await repo.get(rec_id)

                if not model:
                    return None

                from avatarfactory.models.schemas import RecommendationStatus

                return RecommendedPersona(
                    id=model.id,
                    created_at=model.created_at,
                    source_platforms=model.source_platforms,
                    source_trends=model.source_trends,
                    name=model.name,
                    tagline=model.tagline,
                    domain=model.domain,
                    expertise=model.expertise,
                    target_audience=model.target_audience,
                    audience_pain_points=model.audience_pain_points,
                    suggested_tone=model.suggested_tone,
                    content_types=model.content_types,
                    content_pillars=model.content_pillars,
                    relevance_score=model.relevance_score,
                    potential_score=model.potential_score,
                    rationale=model.rationale,
                    status=RecommendationStatus(model.status) if model.status else RecommendationStatus.ACTIVE,
                    adopted_persona_id=model.adopted_persona_id,
                )

        return _run_async(_get())

    def mark_recommendation_adopted(
        self,
        rec_id: str,
        persona_id: str,
    ) -> bool:
        """Mark a recommendation as adopted."""
        async def _mark():
            async with get_session() as session:
                repo = RecommendedPersonaRepository(session)
                return await repo.mark_adopted(rec_id, persona_id)

        return _run_async(_mark())

    # ========================================================================
    # Trend Snapshots
    # ========================================================================

    def save_trend_snapshot(self, snapshot: TrendSnapshot) -> str:
        """Save a trend snapshot."""
        async def _save():
            async with get_session() as session:
                repo = TrendSnapshotRepository(session)

                model = TrendSnapshotModel(
                    id=f"{snapshot.captured_at.strftime('%Y-%m-%d')}_{snapshot.platform}",
                    platform=snapshot.platform,
                    captured_at=snapshot.captured_at,
                    trending_topics=snapshot.trending_topics,
                    trending_hashtags=snapshot.trending_hashtags,
                    top_posts=[p.model_dump() if hasattr(p, 'model_dump') else p for p in snapshot.top_posts] if snapshot.top_posts else None,
                    analysis_summary=snapshot.analysis_summary,
                    key_themes=snapshot.key_themes,
                    content_patterns=snapshot.content_patterns,
                )
                await repo.save(model)
                return model.id

        return _run_async(_save())

    def get_latest_trend_snapshots(
        self,
        platform: Optional[str] = None,
        limit: int = 5,
    ) -> List[TrendSnapshot]:
        """Get latest trend snapshots."""
        async def _get():
            async with get_session() as session:
                repo = TrendSnapshotRepository(session)

                if platform:
                    models = await repo.list_by_platform(platform, limit=limit)
                else:
                    models = await repo.list(limit=limit, order_by="-captured_at")

                return [
                    TrendSnapshot(
                        id=m.id,
                        platform=m.platform,
                        captured_at=m.captured_at,
                        trending_topics=m.trending_topics or [],
                        trending_hashtags=m.trending_hashtags or [],
                        top_posts=m.top_posts or [],
                        analysis_summary=m.analysis_summary or "",
                        key_themes=m.key_themes or [],
                        content_patterns=m.content_patterns or [],
                    )
                    for m in models
                ]

        return _run_async(_get())

    # ========================================================================
    # Batch Loading Methods (Performance Optimization)
    # ========================================================================

    def list_personas_summary(self) -> List[Dict[str, Any]]:
        """Batch load all persona summaries."""
        async def _list():
            async with get_session() as session:
                repo = PersonaRepository(session)
                personas = await repo.list_active()

                return [
                    {
                        "id": p.id,
                        "name": p.name,
                        "tagline": p.tagline,
                        "expertise": p.expertise,
                        "platforms": p.platforms,
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                        "version": p.version,
                    }
                    for p in personas
                ]

        return _run_async(_list())

    def get_batch_persona_stats(
        self,
        persona_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Batch calculate statistics for multiple personas efficiently."""
        async def _get():
            async with get_session() as session:
                repo = PersonaRepository(session)

                if persona_ids is None:
                    personas = await repo.list_active()
                    ids = [p.id for p in personas]
                else:
                    ids = persona_ids

                raw_stats = await repo.get_batch_stats(ids)

                # Transform to match file-based KnowledgeBase format
                result = {}
                for pid, s in raw_stats.items():
                    draft = s.get("draft_count", 0)
                    published = s.get("published_count", 0)
                    result[pid] = {
                        "persona_id": pid,
                        "total_content": draft + published,
                        "published_content": published,
                        "draft_content": draft,
                        "discovery_count": s.get("discovery_count", 0),
                        "ideas_count": s.get("ideas_count", 0),
                        "avg_review_score": 0,  # Not calculated in batch for now
                        "content_by_pillar": {},
                        "content_by_platform": {},
                        "score_distribution": {},
                    }
                return result

        return _run_async(_get())

    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        async def _get():
            async with get_session() as session:
                from sqlalchemy import select, func

                persona_count = await session.execute(
                    select(func.count()).select_from(PersonaModel).where(PersonaModel.is_deleted.is_(False))
                )
                draft_count = await session.execute(
                    select(func.count()).select_from(ContentModel).where(ContentModel.status == "draft")
                )
                published_count = await session.execute(
                    select(func.count()).select_from(ContentModel).where(ContentModel.status == "published")
                )

                return {
                    "total_personas": persona_count.scalar() or 0,
                    "draft_contents": draft_count.scalar() or 0,
                    "published_contents": published_count.scalar() or 0,
                    "total_experiments": 0,  # Experiments not migrated to DB yet
                }

        return _run_async(_get())

    # ========================================================================
    # Simulation Reports
    # ========================================================================

    def save_simulation_report(
        self, report: SimulationReport, persona_id: str
    ) -> None:
        """Save simulation report."""
        async def _save():
            async with get_session() as session:
                from sqlalchemy import select

                # Check if simulation exists
                query = select(SimulationModel).where(
                    SimulationModel.content_id == report.content_id
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()

                sim_data = {
                    "content_id": report.content_id,
                    "simulated_at": report.simulated_at or datetime.utcnow(),
                    "predicted_engagement": report.predicted_engagement.model_dump() if report.predicted_engagement else {},
                    "audience_reaction": report.audience_reaction.model_dump() if report.audience_reaction else {},
                    "recommended_timing": report.recommended_timing.model_dump() if report.recommended_timing else None,
                    "risk_factors": [r.model_dump() for r in report.risk_factors] if report.risk_factors else None,
                    "confidence_score": report.confidence_score,
                }

                if existing:
                    for key, value in sim_data.items():
                        if key != "content_id":
                            setattr(existing, key, value)
                    await session.flush()
                else:
                    model = SimulationModel(**sim_data)
                    session.add(model)
                    await session.flush()

        _run_async(_save())

    def load_simulation_report(
        self, content_id: str, persona_id: str
    ) -> Optional[SimulationReport]:
        """Load simulation report."""
        async def _load():
            async with get_session() as session:
                from sqlalchemy import select
                from avatarfactory.models.schemas import (
                    PredictedEngagement,
                    AudienceReaction,
                    RecommendedTiming,
                    RiskFactor,
                )

                query = select(SimulationModel).where(
                    SimulationModel.content_id == content_id
                )
                result = await session.execute(query)
                model = result.scalar_one_or_none()

                if not model:
                    return None

                return SimulationReport(
                    content_id=model.content_id,
                    simulated_at=model.simulated_at,
                    predicted_engagement=PredictedEngagement(**model.predicted_engagement) if model.predicted_engagement else None,
                    audience_reaction=AudienceReaction(**model.audience_reaction) if model.audience_reaction else None,
                    recommended_timing=RecommendedTiming(**model.recommended_timing) if model.recommended_timing else None,
                    risk_factors=[RiskFactor(**r) for r in model.risk_factors] if model.risk_factors else None,
                    confidence_score=model.confidence_score,
                )

        return _run_async(_load())

    # ========================================================================
    # Experiments (File-based fallback - experiments not critical for DB)
    # ========================================================================

    def save_experiment(self, experiment: "Experiment") -> None:
        """Save experiment (falls back to file storage)."""
        # Experiments are not migrated to DB, use file-based storage
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        kb.save_experiment(experiment)

    def load_experiment(self, experiment_id: str) -> Optional["Experiment"]:
        """Load experiment (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        return kb.load_experiment(experiment_id)

    def list_experiments(self, persona_id: Optional[str] = None) -> List["Experiment"]:
        """List experiments (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        return kb.list_experiments(persona_id)

    # ========================================================================
    # Retrospectives (File-based fallback)
    # ========================================================================

    def save_retrospective(self, retro: "WeeklyRetrospective") -> None:
        """Save weekly retrospective (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        kb.save_retrospective(retro)

    def load_retrospective(
        self, week: str, persona_id: str
    ) -> Optional["WeeklyRetrospective"]:
        """Load retrospective by week (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        return kb.load_retrospective(week, persona_id)

    def list_retrospectives(self, persona_id: str) -> List["WeeklyRetrospective"]:
        """List all retrospectives for a persona (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        return kb.list_retrospectives(persona_id)

    # ========================================================================
    # Platform Rules (File-based fallback)
    # ========================================================================

    def save_platform_rules(self, platform: str, rules: Dict[str, Any]) -> None:
        """Save platform-specific rules (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        kb.save_platform_rules(platform, rules)

    def load_platform_rules(self, platform: str) -> Optional[Dict[str, Any]]:
        """Load platform-specific rules (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        return kb.load_platform_rules(platform)

    # ========================================================================
    # Evolution Management
    # ========================================================================

    def save_evolution_suggestion(
        self, persona_id: str, suggestion: EvolutionSuggestion
    ) -> None:
        """Save an evolution suggestion."""
        async def _save():
            async with get_session() as session:
                from sqlalchemy import select

                # Check if exists
                query = select(EvolutionSuggestionModel).where(
                    EvolutionSuggestionModel.id == suggestion.id
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()

                model_data = {
                    "id": suggestion.id,
                    "persona_id": persona_id,
                    "created_at": suggestion.created_at or datetime.utcnow(),
                    "trigger_type": suggestion.trigger_type,
                    "source_data": suggestion.source_data,
                    "suggested_changes": [c.model_dump() for c in suggestion.suggested_changes] if suggestion.suggested_changes else [],
                    "rationale": suggestion.rationale,
                    "expected_impact": suggestion.expected_impact,
                    "status": suggestion.status.value if hasattr(suggestion.status, 'value') else str(suggestion.status),
                    "applied_at": suggestion.applied_at,
                    "applied_version": suggestion.applied_version,
                }

                if existing:
                    for key, value in model_data.items():
                        if key != "id":
                            setattr(existing, key, value)
                    await session.flush()
                else:
                    model = EvolutionSuggestionModel(**model_data)
                    session.add(model)
                    await session.flush()

        _run_async(_save())

    def load_evolution_suggestion(
        self, persona_id: str, suggestion_id: str
    ) -> Optional[EvolutionSuggestion]:
        """Load a specific evolution suggestion."""
        async def _load():
            async with get_session() as session:
                from sqlalchemy import select
                from avatarfactory.models.schemas import SuggestedChange, EvolutionStatus

                query = select(EvolutionSuggestionModel).where(
                    EvolutionSuggestionModel.id == suggestion_id
                )
                result = await session.execute(query)
                model = result.scalar_one_or_none()

                if not model:
                    return None

                return EvolutionSuggestion(
                    id=model.id,
                    created_at=model.created_at,
                    trigger_type=model.trigger_type,
                    source_data=model.source_data,
                    suggested_changes=[SuggestedChange(**c) for c in model.suggested_changes] if model.suggested_changes else [],
                    rationale=model.rationale,
                    expected_impact=model.expected_impact,
                    status=EvolutionStatus(model.status) if model.status else EvolutionStatus.PENDING,
                    applied_at=model.applied_at,
                    applied_version=model.applied_version,
                )

        return _run_async(_load())

    def list_evolution_suggestions(
        self,
        persona_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[EvolutionSuggestion]:
        """List evolution suggestions for a persona."""
        async def _list():
            async with get_session() as session:
                from sqlalchemy import select
                from avatarfactory.models.schemas import SuggestedChange, EvolutionStatus

                query = (
                    select(EvolutionSuggestionModel)
                    .where(EvolutionSuggestionModel.persona_id == persona_id)
                    .order_by(EvolutionSuggestionModel.created_at.desc())
                    .limit(limit)
                )

                if status:
                    query = query.where(EvolutionSuggestionModel.status == status)

                result = await session.execute(query)
                models = result.scalars().all()

                return [
                    EvolutionSuggestion(
                        id=m.id,
                        created_at=m.created_at,
                        trigger_type=m.trigger_type,
                        source_data=m.source_data,
                        suggested_changes=[SuggestedChange(**c) for c in m.suggested_changes] if m.suggested_changes else [],
                        rationale=m.rationale,
                        expected_impact=m.expected_impact,
                        status=EvolutionStatus(m.status) if m.status else EvolutionStatus.PENDING,
                        applied_at=m.applied_at,
                        applied_version=m.applied_version,
                    )
                    for m in models
                ]

        return _run_async(_list())

    def save_feedback_analysis(
        self, persona_id: str, analysis: "EvolutionFeedbackAnalysis"
    ) -> None:
        """Save feedback analysis results (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        kb.save_feedback_analysis(persona_id, analysis)

    def load_feedback_analysis(
        self, persona_id: str
    ) -> Optional["EvolutionFeedbackAnalysis"]:
        """Load latest feedback analysis (falls back to file storage)."""
        from avatarfactory.core.knowledges import KnowledgeBase
        kb = KnowledgeBase(str(self.base_path))
        return kb.load_feedback_analysis(persona_id)

    def save_agent_config(
        self, persona_id: str, agent_type: str, config: "AgentConfig"
    ) -> None:
        """Save per-persona agent configuration."""
        persona = self.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        if persona.agent_configs is None:
            persona.agent_configs = {}
        persona.agent_configs[agent_type] = config

        self.save_persona(persona)

    def load_agent_config(
        self, persona_id: str, agent_type: str
    ) -> Optional["AgentConfig"]:
        """Load per-persona agent configuration."""
        from avatarfactory.models.schemas import AgentConfig

        persona = self.load_persona(persona_id)
        if not persona or not persona.agent_configs:
            return None

        config_data = persona.agent_configs.get(agent_type)
        if config_data is None:
            return None

        if isinstance(config_data, AgentConfig):
            return config_data

        return AgentConfig(**config_data)

    def get_persona_version(
        self, persona_id: str, version: str
    ) -> Optional[Persona]:
        """Load a specific version of a persona."""
        async def _get():
            async with get_session() as session:
                from sqlalchemy import select

                query = select(PersonaVersionModel).where(
                    PersonaVersionModel.persona_id == persona_id,
                    PersonaVersionModel.version == version,
                )
                result = await session.execute(query)
                version_model = result.scalar_one_or_none()

                if not version_model or not version_model.config_snapshot:
                    return None

                return Persona(**version_model.config_snapshot)

        return _run_async(_get())

    def list_persona_versions(self, persona_id: str) -> List[str]:
        """List all available versions of a persona."""
        async def _list():
            async with get_session() as session:
                from sqlalchemy import select

                query = (
                    select(PersonaVersionModel.version)
                    .where(PersonaVersionModel.persona_id == persona_id)
                    .order_by(PersonaVersionModel.timestamp.desc())
                )
                result = await session.execute(query)
                return [row[0] for row in result.all()]

        return _run_async(_list())

    # ========================================================================
    # Additional Discovery Methods
    # ========================================================================

    def list_discovery_platforms(self, persona_id: str) -> List[str]:
        """List platforms with discovery results for a persona."""
        async def _list():
            async with get_session() as session:
                from sqlalchemy import select, distinct

                query = (
                    select(distinct(DiscoveryResultModel.platform))
                    .where(DiscoveryResultModel.persona_id == persona_id)
                )
                result = await session.execute(query)
                return [row[0] for row in result.all()]

        return _run_async(_list())

    # ========================================================================
    # Additional Recommendation Methods
    # ========================================================================

    def get_latest_recommendations(
        self,
        limit: int = 5,
    ) -> List[RecommendedPersona]:
        """Get most recent active recommendations."""
        return self.get_recommended_personas(limit=limit, status="active")

    def get_today_trend_snapshots(self) -> List[TrendSnapshot]:
        """Get all trend snapshots from today."""
        async def _get():
            async with get_session() as session:
                from sqlalchemy import select

                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                query = (
                    select(TrendSnapshotModel)
                    .where(TrendSnapshotModel.captured_at >= today_start)
                    .order_by(TrendSnapshotModel.captured_at.desc())
                )
                result = await session.execute(query)
                models = result.scalars().all()

                return [
                    TrendSnapshot(
                        id=m.id,
                        platform=m.platform,
                        captured_at=m.captured_at,
                        trending_topics=m.trending_topics or [],
                        trending_hashtags=m.trending_hashtags or [],
                        top_posts=m.top_posts or [],
                        analysis_summary=m.analysis_summary or "",
                        key_themes=m.key_themes or [],
                        content_patterns=m.content_patterns or [],
                    )
                    for m in models
                ]

        return _run_async(_get())

    # ========================================================================
    # Batch Loading Methods (Additional)
    # ========================================================================

    def list_content_with_reviews_batch(
        self,
        persona_id: Optional[str] = None,
        status: str = "draft",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Batch load content with their reviews to avoid N+1 queries."""
        async def _list():
            async with get_session() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                query = (
                    select(ContentModel)
                    .options(selectinload(ContentModel.review))
                    .where(ContentModel.status == status)
                    .order_by(ContentModel.created_at.desc())
                    .limit(limit)
                )

                if persona_id:
                    query = query.where(ContentModel.persona_id == persona_id)

                result = await session.execute(query)
                models = result.scalars().all()

                contents = []
                for m in models:
                    content_data = {
                        "id": m.id,
                        "persona_id": m.persona_id,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "title": m.title,
                        "body": m.body,
                        "pillar": m.pillar,
                        "platform": m.platform,
                        "content_type": m.content_type,
                        "tags": m.tags,
                        "_status": status,
                    }

                    if m.review:
                        content_data["review"] = {
                            "overall_score": m.review.overall_score,
                            "reviewed_at": m.review.reviewed_at.isoformat() if m.review.reviewed_at else None,
                            "persona_consistency": m.review.persona_consistency_score,
                            "platform_fit": m.review.platform_fit_score,
                            "compliance": m.review.compliance_score,
                            "engagement_potential": m.review.engagement_potential_score,
                        }
                    else:
                        content_data["review"] = None

                    contents.append(content_data)

                return contents

        return _run_async(_list())

    def get_all_reviews_batch(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Batch load all reviews across personas."""
        async def _get():
            async with get_session() as session:
                from sqlalchemy import select

                query = select(ReviewModel)

                if persona_id:
                    query = (
                        query.join(ContentModel)
                        .where(ContentModel.persona_id == persona_id)
                    )

                result = await session.execute(query)
                models = result.scalars().all()

                reviews = {}
                for m in models:
                    reviews[m.content_id] = {
                        "content_id": m.content_id,
                        "reviewed_at": m.reviewed_at.isoformat() if m.reviewed_at else None,
                        "overall_score": m.overall_score,
                        "persona_consistency": m.persona_consistency,
                        "platform_fit": m.platform_fit,
                        "compliance": m.compliance,
                        "engagement_potential": m.engagement_potential,
                        "suggestions": m.suggestions,
                    }

                return reviews

        return _run_async(_get())

    # ========================================================================
    # Utilities
    # ========================================================================

    def export_persona_data(self, persona_id: str, export_path: str) -> None:
        """Export all data for a persona to a zip file."""
        import shutil
        import tempfile
        import json

        # Create temp directory with persona data
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / persona_id

            # Export persona config
            persona = self.load_persona(persona_id)
            if not persona:
                raise ValueError(f"Persona {persona_id} not found")

            tmppath.mkdir()
            config_path = tmppath / "config.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(persona.model_dump(mode="json"), f, indent=2)

            # Export content
            content_dir = tmppath / "content"
            content_dir.mkdir()

            for status in ["draft", "published"]:
                contents = self.list_content(persona_id=persona_id, status=status)
                for c in contents:
                    cpath = content_dir / f"{c.id}_{status}.json"
                    with open(cpath, "w", encoding="utf-8") as f:
                        json.dump(c.model_dump(mode="json"), f, indent=2)

            # Export version history
            versions = self.get_persona_history(persona_id)
            if versions:
                history_path = tmppath / "history.json"
                with open(history_path, "w", encoding="utf-8") as f:
                    json.dump([v.model_dump(mode="json") for v in versions], f, indent=2)

            # Create zip
            shutil.make_archive(export_path, "zip", tmppath)


def get_knowledge_base(base_path: str = "./knowledges") -> Any:
    """
    Factory function to get the appropriate KnowledgeBase implementation.

    If AVATARFACTORY_USE_DB is set to "true", returns database-backed implementation.
    Otherwise returns the file-based implementation for backwards compatibility.

    Args:
        base_path: Base path for storage

    Returns:
        KnowledgeBase or KnowledgeBaseDB instance
    """
    use_db = os.getenv("AVATARFACTORY_USE_DB", "").lower() == "true"

    if use_db:
        return KnowledgeBaseDB(base_path)
    else:
        from avatarfactory.core.knowledges import KnowledgeBase
        return KnowledgeBase(base_path)
