"""
Chronicle API Routes.

Provides API endpoints for the Chronicle (Avatar养成记) SSR website.
These endpoints return data for server-side rendering via the Astro framework.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from avatarfactory.service.cache import (
    dashboard_cache,
    stats_cache,
    persona_cache,
    get_or_set_async,
)

router = APIRouter(prefix="/api/chronicle", tags=["Chronicle"])
logger = logging.getLogger(__name__)


def _get_orchestrator():
    """Get the orchestrator instance from app state."""
    try:
        from avatarfactory.service.app import get_orchestrator
        return get_orchestrator()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get orchestrator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )


# =============================================================================
# Persona Endpoints
# =============================================================================


@router.get("/personas")
async def list_personas() -> Dict[str, Any]:
    """Get all personas with basic info (cached)."""
    # Try cache first
    cache_key = "chronicle:personas:list"
    cached = persona_cache.get(cache_key)
    if cached is not None:
        return cached

    orchestrator = _get_orchestrator()
    persona_ids = orchestrator.kb.list_personas()
    personas = []

    for pid in persona_ids:
        persona = orchestrator.kb.load_persona(pid)
        if persona:
            personas.append({
                "id": persona.id,
                "version": persona.version,
                "created_at": persona.created_at.isoformat() if persona.created_at else None,
                "updated_at": persona.updated_at.isoformat() if persona.updated_at else None,
                "identity": {
                    "name": persona.identity.name,
                    "tagline": persona.identity.tagline,
                    "expertise": persona.identity.expertise,
                },
                "target_audience": {
                    "primary": persona.target_audience.primary,
                    "pain_points": persona.target_audience.pain_points,
                    "goals": persona.target_audience.goals,
                },
                "voice_style": {
                    "tone": persona.voice_style.tone,
                    "language_patterns": persona.voice_style.language_patterns,
                    "emoji_usage": persona.voice_style.emoji_usage,
                },
                "content_pillars": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "frequency": p.frequency,
                        "examples": p.examples,
                    }
                    for p in persona.content_pillars
                ],
                "boundaries": {
                    "avoid": persona.boundaries.avoid if persona.boundaries else [],
                    "compliance": persona.boundaries.compliance if persona.boundaries else [],
                },
                "platforms": [pt.value for pt in persona.platforms],
                "notification": persona.notification.model_dump() if persona.notification else None,
            })

    result = {
        "count": len(personas),
        "personas": personas,
    }

    # Cache the result
    persona_cache.set(cache_key, result)
    return result


@router.get("/personas/ids")
async def list_persona_ids() -> List[str]:
    """Get all persona IDs."""
    orchestrator = _get_orchestrator()
    return orchestrator.kb.list_personas()


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str) -> Optional[Dict[str, Any]]:
    """Get a single persona by ID."""
    orchestrator = _get_orchestrator()
    persona = orchestrator.kb.load_persona(persona_id)

    if not persona:
        return None

    return {
        "id": persona.id,
        "version": persona.version,
        "created_at": persona.created_at.isoformat() if persona.created_at else None,
        "updated_at": persona.updated_at.isoformat() if persona.updated_at else None,
        "identity": {
            "name": persona.identity.name,
            "tagline": persona.identity.tagline,
            "expertise": persona.identity.expertise,
        },
        "target_audience": {
            "primary": persona.target_audience.primary,
            "pain_points": persona.target_audience.pain_points,
            "goals": persona.target_audience.goals,
        },
        "voice_style": {
            "tone": persona.voice_style.tone,
            "language_patterns": persona.voice_style.language_patterns,
            "emoji_usage": persona.voice_style.emoji_usage,
        },
        "content_pillars": [
            {
                "name": p.name,
                "description": p.description,
                "frequency": p.frequency,
                "examples": p.examples,
            }
            for p in persona.content_pillars
        ],
        "boundaries": {
            "avoid": persona.boundaries.avoid if persona.boundaries else [],
            "compliance": persona.boundaries.compliance if persona.boundaries else [],
        },
        "platforms": [pt.value for pt in persona.platforms],
        "notification": persona.notification.model_dump() if persona.notification else None,
    }


@router.get("/personas/{persona_id}/stats")
async def get_persona_stats(persona_id: str) -> Dict[str, Any]:
    """Get statistics for a persona."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        orchestrator = _get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Get content for this persona
        all_content = orchestrator.kb.list_content(persona_id=persona_id, status="draft")
        published_content = orchestrator.kb.list_content(persona_id=persona_id, status="published")

        # Combine content lists
        contents = all_content + published_content

        content_by_pillar: Dict[str, int] = {}
        content_by_platform: Dict[str, int] = {}
        total_consistency = 0
        total_platform_fit = 0
        total_compliance = 0
        total_engagement = 0
        review_count = 0

        for content in contents:
            try:
                pillar = content.pillar or "unknown"
                platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)

                content_by_pillar[pillar] = content_by_pillar.get(pillar, 0) + 1
                content_by_platform[platform] = content_by_platform.get(platform, 0) + 1

                # Load review for this content
                review = orchestrator.kb.load_review_report(content.id, persona_id)
                if review:
                    total_consistency += review.persona_consistency.score
                    total_platform_fit += review.platform_fit.score
                    total_compliance += review.compliance.score
                    total_engagement += review.engagement_potential.score
                    review_count += 1
            except Exception as e:
                logger.warning(f"Error processing content {content.id}: {e}")
                continue

        avg_score = 0
        if review_count > 0:
            avg_score = (total_consistency + total_platform_fit + total_compliance + total_engagement) / (review_count * 4)

        return {
            "persona_id": persona_id,
            "total_content": len(contents),
            "published_content": len(published_content),
            "draft_content": len(all_content),
            "avg_review_score": round(avg_score),
            "content_by_pillar": content_by_pillar,
            "content_by_platform": content_by_platform,
            "score_distribution": {
                "persona_consistency": round(total_consistency / review_count) if review_count > 0 else 0,
                "platform_fit": round(total_platform_fit / review_count) if review_count > 0 else 0,
                "compliance": round(total_compliance / review_count) if review_count > 0 else 0,
                "engagement_potential": round(total_engagement / review_count) if review_count > 0 else 0,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona stats for {persona_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting persona stats: {str(e)}",
        )


@router.get("/personas/{persona_id}/history")
async def get_persona_history(persona_id: str) -> List[Dict[str, Any]]:
    """Get version history for a persona."""
    orchestrator = _get_orchestrator()

    # Verify persona exists
    persona = orchestrator.kb.load_persona(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {persona_id} not found",
        )

    history = orchestrator.kb.get_persona_history(persona_id)
    return [
        {
            "version": v.version,
            "timestamp": v.timestamp.isoformat() if hasattr(v.timestamp, 'isoformat') else str(v.timestamp),
            "changes": v.changes,
            "reason": v.reason,
            "expected_impact": v.expected_impact,
            "author": v.author,
            "approved": v.approved,
        }
        for v in history
    ]


@router.get("/personas/{persona_id}/versions")
async def get_persona_versions(persona_id: str) -> List[str]:
    """Get available version IDs for a persona."""
    orchestrator = _get_orchestrator()
    return orchestrator.kb.list_persona_versions(persona_id)


@router.get("/personas/{persona_id}/content")
async def get_persona_content(persona_id: str) -> List[Dict[str, Any]]:
    """Get all content for a persona."""
    orchestrator = _get_orchestrator()

    # Verify persona exists
    persona = orchestrator.kb.load_persona(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {persona_id} not found",
        )

    drafts = orchestrator.kb.list_content(persona_id=persona_id, status="draft")
    published = orchestrator.kb.list_content(persona_id=persona_id, status="published")

    contents = []

    # Process drafts - exclude ones that have been published
    published_ids = {c.id for c in published}
    for c in drafts:
        if c.id not in published_ids:
            contents.append(_content_to_dict(c, "draft"))

    # Process published
    for c in published:
        contents.append(_content_to_dict(c, "published"))

    # Sort by created_at descending
    contents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return contents


@router.get("/personas/{persona_id}/timeline")
async def get_persona_timeline(
    persona_id: str,
    limit: int = Query(50, ge=1, le=500)
) -> List[Dict[str, Any]]:
    """Get timeline events for a persona."""
    orchestrator = _get_orchestrator()

    # Verify persona exists
    persona = orchestrator.kb.load_persona(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {persona_id} not found",
        )

    return await _build_timeline_events(orchestrator, persona_id=persona_id, limit=limit)


# =============================================================================
# Content Endpoints
# =============================================================================


def _content_to_dict(content, status: str) -> Dict[str, Any]:
    """Convert content object to dictionary."""
    platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
    return {
        "id": content.id,
        "persona_id": content.persona_id,
        "created_at": content.created_at.isoformat() if content.created_at else None,
        "title": content.title,
        "body": content.body,
        "pillar": content.pillar,
        "platform": platform,
        "structure": {
            "sections": content.structure.sections if content.structure else [],
            "style_constraints": content.structure.style_constraints if content.structure else {},
        } if content.structure else None,
        "tags": content.tags,
        "metadata": content.metadata,
        "review_score": content.review_score,
        "review_issues": content.review_issues,
        "predicted_engagement": content.predicted_engagement,
        "status": status,
    }


@router.get("/content")
async def list_all_content(
    limit: int = Query(100, ge=1, le=500)
) -> List[Dict[str, Any]]:
    """Get all content across all personas (cached)."""
    # Try cache first
    cache_key = f"chronicle:content:list:{limit}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached

    orchestrator = _get_orchestrator()
    persona_ids = orchestrator.kb.list_personas()

    all_content = []
    for pid in persona_ids:
        drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
        published = orchestrator.kb.list_content(persona_id=pid, status="published")

        published_ids = {c.id for c in published}
        for c in drafts:
            if c.id not in published_ids:
                all_content.append(_content_to_dict(c, "draft"))

        for c in published:
            all_content.append(_content_to_dict(c, "published"))

    # Sort by created_at descending
    all_content.sort(key=lambda x: x.get("created_at", "") or "", reverse=True)
    result = all_content[:limit]

    # Cache the result
    stats_cache.set(cache_key, result)
    return result


@router.get("/content/ids")
async def list_all_content_ids() -> List[str]:
    """Get all content IDs."""
    orchestrator = _get_orchestrator()
    persona_ids = orchestrator.kb.list_personas()

    all_ids = []
    for pid in persona_ids:
        drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
        published = orchestrator.kb.list_content(persona_id=pid, status="published")
        all_ids.extend(c.id for c in drafts)
        all_ids.extend(c.id for c in published)

    return list(set(all_ids))


@router.get("/content/recent")
async def get_recent_content(
    limit: int = Query(10, ge=1, le=100)
) -> List[Dict[str, Any]]:
    """Get most recent content."""
    return await list_all_content(limit=limit)


@router.get("/content/{content_id}")
async def get_content(content_id: str) -> Optional[Dict[str, Any]]:
    """Get a single content item by ID."""
    orchestrator = _get_orchestrator()

    # Try draft first
    content = orchestrator.kb.load_content(content_id, status="draft")
    content_status = "draft"

    if not content:
        content = orchestrator.kb.load_content(content_id, status="published")
        content_status = "published"

    if not content:
        return None

    return _content_to_dict(content, content_status)


@router.get("/content/{content_id}/review")
async def get_content_review(content_id: str) -> Optional[Dict[str, Any]]:
    """Get review report for a content item."""
    orchestrator = _get_orchestrator()

    # First, find the content to get persona_id
    content = None
    for status in ["draft", "published"]:
        content = orchestrator.kb.load_content(content_id, status=status)
        if content:
            break

    if not content:
        return None

    review = orchestrator.kb.load_review_report(content_id, content.persona_id)

    if not review:
        return None

    return {
        "content_id": review.content_id,
        "reviewed_at": review.reviewed_at.isoformat() if hasattr(review.reviewed_at, 'isoformat') else str(review.reviewed_at),
        "persona_consistency": {
            "score": review.persona_consistency.score,
            "issues": review.persona_consistency.issues,
            "strengths": review.persona_consistency.strengths,
            "reasoning": review.persona_consistency.reasoning,
        },
        "platform_fit": {
            "score": review.platform_fit.score,
            "issues": review.platform_fit.issues,
            "strengths": review.platform_fit.strengths,
            "reasoning": review.platform_fit.reasoning,
        },
        "compliance": {
            "score": review.compliance.score,
            "risk_level": review.compliance.risk_level,
            "checks": review.compliance.checks,
            "issues": review.compliance.issues,
        },
        "engagement_potential": {
            "score": review.engagement_potential.score,
            "issues": review.engagement_potential.issues,
            "strengths": review.engagement_potential.strengths,
            "reasoning": review.engagement_potential.reasoning,
        },
        "overall_score": review.overall_score,
        "suggestions": {
            "critical": review.suggestions.critical if review.suggestions else [],
            "recommended": review.suggestions.recommended if review.suggestions else [],
            "optional": review.suggestions.optional if review.suggestions else [],
        },
    }


# =============================================================================
# Scheduler Endpoints
# =============================================================================


@router.get("/scheduler/tasks")
async def list_tasks() -> List[Dict[str, Any]]:
    """Get all scheduled tasks."""
    from avatarfactory.service.app import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return []

    tasks = scheduler.list_tasks()
    return [
        {
            "id": t.id,
            "name": t.name,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "enabled": t.enabled,
            "persona_id": t.persona_id,
            "platform": t.platform,
            "extra_params": t.extra_params,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "last_status": t.last_status,
            "last_error": t.last_error,
            "run_count": t.run_count,
        }
        for t in tasks
    ]


@router.get("/scheduler/tasks/{task_id}")
async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a single task by ID."""
    from avatarfactory.service.app import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return None

    task = scheduler.get_task(task_id)
    if not task:
        return None

    return {
        "id": task.id,
        "name": task.name,
        "task_type": task.task_type,
        "schedule": task.schedule,
        "enabled": task.enabled,
        "persona_id": task.persona_id,
        "platform": task.platform,
        "extra_params": task.extra_params,
        "last_run": task.last_run.isoformat() if task.last_run else None,
        "last_status": task.last_status,
        "last_error": task.last_error,
        "run_count": task.run_count,
    }


@router.get("/scheduler/tasks/by-persona/{persona_id}")
async def get_tasks_by_persona(persona_id: str) -> List[Dict[str, Any]]:
    """Get tasks for a specific persona."""
    from avatarfactory.service.app import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return []

    tasks = [t for t in scheduler.list_tasks() if t.persona_id == persona_id]
    return [
        {
            "id": t.id,
            "name": t.name,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "enabled": t.enabled,
            "persona_id": t.persona_id,
            "platform": t.platform,
            "extra_params": t.extra_params,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "last_status": t.last_status,
            "last_error": t.last_error,
            "run_count": t.run_count,
        }
        for t in tasks
    ]


@router.get("/scheduler/tasks/active")
async def get_active_tasks() -> List[Dict[str, Any]]:
    """Get all enabled tasks."""
    from avatarfactory.service.app import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return []

    tasks = [t for t in scheduler.list_tasks() if t.enabled]
    return [
        {
            "id": t.id,
            "name": t.name,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "enabled": t.enabled,
            "persona_id": t.persona_id,
            "platform": t.platform,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "last_status": t.last_status,
            "run_count": t.run_count,
        }
        for t in tasks
    ]


@router.get("/scheduler/stats")
async def get_task_stats() -> Dict[str, Any]:
    """Get scheduler statistics."""
    from avatarfactory.service.app import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return {
            "total": 0,
            "active": 0,
            "byType": {},
            "successRate": 0,
        }

    tasks = scheduler.list_tasks()
    active = [t for t in tasks if t.enabled]

    by_type: Dict[str, int] = {}
    success_count = 0
    total_runs = 0

    for task in tasks:
        by_type[task.task_type] = by_type.get(task.task_type, 0) + 1
        if task.run_count > 0:
            total_runs += task.run_count
            if task.last_status == "success":
                success_count += task.run_count

    return {
        "total": len(tasks),
        "active": len(active),
        "byType": by_type,
        "successRate": round((success_count / total_runs) * 100) if total_runs > 0 else 0,
    }


# =============================================================================
# Dashboard Endpoint (Optimized - Single API call)
# =============================================================================


@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """
    Get all dashboard data in a single API call.

    This endpoint combines personas, stats, recent content, timeline,
    and tasks into a single response to minimize network roundtrips.

    Returns cached data when available (30 second TTL).
    """
    cache_key = "dashboard"

    async def build_dashboard():
        from avatarfactory.service.app import get_scheduler

        orchestrator = _get_orchestrator()
        scheduler = get_scheduler()

        # Use batch loading methods for efficiency
        persona_summaries = orchestrator.kb.list_personas_summary()
        batch_stats = orchestrator.kb.get_batch_persona_stats()

        # Build personas with stats
        personas_with_stats = []
        for summary in persona_summaries[:6]:  # Limit to 6 for dashboard
            pid = summary["id"]
            stats = batch_stats.get(pid, {
                "persona_id": pid,
                "total_content": 0,
                "published_content": 0,
                "draft_content": 0,
                "avg_review_score": 0,
                "content_by_pillar": {},
                "content_by_platform": {},
                "score_distribution": {
                    "persona_consistency": 0,
                    "platform_fit": 0,
                    "compliance": 0,
                    "engagement_potential": 0,
                },
            })
            personas_with_stats.append({
                "persona": {
                    "id": summary["id"],
                    "version": summary.get("version", "v1.0"),
                    "created_at": summary.get("created_at"),
                    "updated_at": summary.get("updated_at"),
                    "identity": {
                        "name": summary["name"],
                        "tagline": summary.get("tagline", ""),
                        "expertise": summary.get("expertise", []),
                    },
                    "platforms": summary.get("platforms", []),
                },
                "stats": stats,
            })

        # Get recent content with reviews using batch loading
        recent_content_raw = orchestrator.kb.list_content_with_reviews_batch(
            status="draft", limit=20
        )
        recent_content_raw += orchestrator.kb.list_content_with_reviews_batch(
            status="published", limit=20
        )

        # Deduplicate and sort
        seen_ids = set()
        recent_content = []
        for c in sorted(recent_content_raw, key=lambda x: x.get("created_at") or "", reverse=True):
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                platform = c.get("platform", "")
                if hasattr(platform, "value"):
                    platform = platform.value
                recent_content.append({
                    "id": c["id"],
                    "persona_id": c.get("persona_id"),
                    "created_at": c.get("created_at"),
                    "title": c.get("title", ""),
                    "body": c.get("body", ""),
                    "pillar": c.get("pillar"),
                    "platform": platform,
                    "tags": c.get("tags", []),
                    "review_score": c.get("review", {}).get("overall_score") if c.get("review") else c.get("review_score"),
                    "status": c.get("_status", "draft"),
                })
                if len(recent_content) >= 6:
                    break

        # Build timeline events efficiently
        timeline_events = await _build_timeline_events_optimized(orchestrator, limit=10)

        # Get active tasks
        active_tasks = []
        if scheduler:
            tasks = [t for t in scheduler.list_tasks() if t.enabled]
            for t in tasks[:5]:
                active_tasks.append({
                    "id": t.id,
                    "name": t.name,
                    "task_type": t.task_type,
                    "schedule": t.schedule,
                    "enabled": t.enabled,
                    "persona_id": t.persona_id,
                    "platform": t.platform,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "last_status": t.last_status,
                    "run_count": t.run_count,
                })

        # Calculate global stats from batch stats
        total_content = sum(s.get("total_content", 0) for s in batch_stats.values())
        total_published = sum(s.get("published_content", 0) for s in batch_stats.values())
        total_drafts = sum(s.get("draft_content", 0) for s in batch_stats.values())
        total_score = sum(s.get("avg_review_score", 0) for s in batch_stats.values())
        score_count = sum(1 for s in batch_stats.values() if s.get("avg_review_score", 0) > 0)

        # Content by day (last 30 days)
        now = datetime.now()
        content_by_day: Dict[str, int] = {}
        for i in range(29, -1, -1):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            content_by_day[date_str] = 0

        for c in recent_content_raw:
            created_at = c.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    date_str = created_at[:10]  # Extract YYYY-MM-DD
                else:
                    date_str = created_at.strftime("%Y-%m-%d")
                if date_str in content_by_day:
                    content_by_day[date_str] += 1

        global_stats = {
            "total_personas": len(persona_summaries),
            "total_content": total_content,
            "total_published": total_published,
            "total_drafts": total_drafts,
            "avg_review_score": round(total_score / score_count) if score_count > 0 else 0,
            "active_tasks": len(active_tasks),
            "content_by_day": [{"date": date, "count": count} for date, count in content_by_day.items()],
        }

        return {
            "personas": personas_with_stats,
            "recentContent": recent_content,
            "timeline": timeline_events,
            "tasks": active_tasks,
            "stats": global_stats,
        }

    return await get_or_set_async(dashboard_cache, cache_key, build_dashboard)


async def _build_timeline_events_optimized(
    orchestrator,
    persona_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Build timeline events using batch loading for better performance.

    Avoids N+1 queries by loading all reviews in batch.
    """
    from avatarfactory.service.app import get_scheduler

    events: List[Dict[str, Any]] = []

    try:
        # Get personas to process
        if persona_id:
            persona_ids = [persona_id]
        else:
            persona_ids = orchestrator.kb.list_personas()

        # Batch load all reviews
        all_reviews = orchestrator.kb.get_all_reviews_batch(persona_id)

        for pid in persona_ids:
            try:
                # Add persona version events from history
                history = orchestrator.kb.get_persona_history(pid)
                for version in history:
                    timestamp = version.timestamp.isoformat() if hasattr(version.timestamp, 'isoformat') else str(version.timestamp)
                    events.append({
                        "id": f"{pid}-{version.version}",
                        "type": "persona_created" if version.version == "v1.0" else "persona_updated",
                        "timestamp": timestamp,
                        "title": "创建人设" if version.version == "v1.0" else f"更新至 {version.version}",
                        "description": ", ".join(version.changes) if version.changes else "",
                        "persona_id": pid,
                        "metadata": {"reason": version.reason, "author": version.author},
                    })
            except Exception as e:
                logger.warning(f"Failed to load history for persona {pid}: {e}")

            try:
                # Add content events
                drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
                published = orchestrator.kb.list_content(persona_id=pid, status="published")

                published_ids = {c.id for c in published}

                for content in drafts:
                    if content.id not in published_ids:
                        timestamp = content.created_at.isoformat() if content.created_at else ""
                        platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
                        events.append({
                            "id": f"content-{content.id}",
                            "type": "content_created",
                            "timestamp": timestamp,
                            "title": "创建草稿",
                            "description": content.title,
                            "persona_id": pid,
                            "content_id": content.id,
                            "metadata": {"platform": platform, "pillar": content.pillar},
                        })

                for content in published:
                    timestamp = content.created_at.isoformat() if content.created_at else ""
                    platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
                    events.append({
                        "id": f"content-{content.id}",
                        "type": "content_published",
                        "timestamp": timestamp,
                        "title": "发布内容",
                        "description": content.title,
                        "persona_id": pid,
                        "content_id": content.id,
                        "metadata": {"platform": platform, "pillar": content.pillar},
                    })

                # Add review events using batch-loaded reviews (no N+1!)
                contents = drafts + published
                for content in contents:
                    review = all_reviews.get(content.id)
                    if review:
                        reviewed_at = review.get("reviewed_at", "")
                        if hasattr(reviewed_at, "isoformat"):
                            timestamp = reviewed_at.isoformat()
                        else:
                            timestamp = str(reviewed_at)
                        events.append({
                            "id": f"review-{content.id}",
                            "type": "review_completed",
                            "timestamp": timestamp,
                            "title": "审核完成",
                            "description": f"评分: {review.get('overall_score', 0)}",
                            "persona_id": pid,
                            "content_id": content.id,
                            "metadata": {"score": review.get("overall_score", 0)},
                        })
            except Exception as e:
                logger.warning(f"Failed to load content/reviews for persona {pid}: {e}")

        # Add task events
        scheduler = get_scheduler()
        if scheduler:
            for task in scheduler.list_tasks():
                if task.last_run and (not persona_id or task.persona_id == persona_id):
                    timestamp = task.last_run.isoformat() if task.last_run else ""
                    events.append({
                        "id": f"task-{task.id}-{timestamp}",
                        "type": "task_executed",
                        "timestamp": timestamp,
                        "title": f"执行任务: {task.name}",
                        "description": "成功" if task.last_status == "success" else f"失败: {task.last_error}",
                        "persona_id": task.persona_id,
                        "metadata": {"task_type": task.task_type, "status": task.last_status},
                    })

    except Exception as e:
        logger.error(f"Failed to build timeline events: {e}")

    # Sort by timestamp descending and limit
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return events[:limit]


@router.post("/personas/batch-stats")
async def get_batch_persona_stats(persona_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get statistics for multiple personas in a single request.

    Args:
        persona_ids: List of persona IDs (optional, defaults to all)

    Returns:
        Dict mapping persona_id to stats
    """
    orchestrator = _get_orchestrator()
    return orchestrator.kb.get_batch_persona_stats(persona_ids)


# =============================================================================
# Timeline & Stats Endpoints
# =============================================================================


async def _build_timeline_events(
    orchestrator,
    persona_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Build timeline events with error handling."""
    from avatarfactory.service.app import get_scheduler

    events: List[Dict[str, Any]] = []

    try:
        # Get personas to process
        if persona_id:
            persona_ids = [persona_id]
        else:
            persona_ids = orchestrator.kb.list_personas()

        for pid in persona_ids:
            try:
                # Add persona version events from history
                history = orchestrator.kb.get_persona_history(pid)
                for version in history:
                    timestamp = version.timestamp.isoformat() if hasattr(version.timestamp, 'isoformat') else str(version.timestamp)
                    events.append({
                        "id": f"{pid}-{version.version}",
                        "type": "persona_created" if version.version == "v1.0" else "persona_updated",
                        "timestamp": timestamp,
                        "title": "创建人设" if version.version == "v1.0" else f"更新至 {version.version}",
                        "description": ", ".join(version.changes) if version.changes else "",
                        "persona_id": pid,
                        "metadata": {"reason": version.reason, "author": version.author},
                    })
            except Exception as e:
                logger.warning(f"Failed to load history for persona {pid}: {e}")

            try:
                # Add content events
                drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
                published = orchestrator.kb.list_content(persona_id=pid, status="published")

                published_ids = {c.id for c in published}

                for content in drafts:
                    if content.id not in published_ids:
                        timestamp = content.created_at.isoformat() if content.created_at else ""
                        platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
                        events.append({
                            "id": f"content-{content.id}",
                            "type": "content_created",
                            "timestamp": timestamp,
                            "title": "创建草稿",
                            "description": content.title,
                            "persona_id": pid,
                            "content_id": content.id,
                            "metadata": {"platform": platform, "pillar": content.pillar},
                        })

                for content in published:
                    timestamp = content.created_at.isoformat() if content.created_at else ""
                    platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
                    events.append({
                        "id": f"content-{content.id}",
                        "type": "content_published",
                        "timestamp": timestamp,
                        "title": "发布内容",
                        "description": content.title,
                        "persona_id": pid,
                        "content_id": content.id,
                        "metadata": {"platform": platform, "pillar": content.pillar},
                    })

                # Add review events
                contents = drafts + published
                for content in contents:
                    review = orchestrator.kb.load_review_report(content.id, pid)
                    if review:
                        timestamp = review.reviewed_at.isoformat() if hasattr(review.reviewed_at, 'isoformat') else str(review.reviewed_at)
                        events.append({
                            "id": f"review-{content.id}",
                            "type": "review_completed",
                            "timestamp": timestamp,
                            "title": "审核完成",
                            "description": f"评分: {review.overall_score}",
                            "persona_id": pid,
                            "content_id": content.id,
                            "metadata": {"score": review.overall_score},
                        })
            except Exception as e:
                logger.warning(f"Failed to load content/reviews for persona {pid}: {e}")

        # Add task events
        scheduler = get_scheduler()
        if scheduler:
            for task in scheduler.list_tasks():
                if task.last_run and (not persona_id or task.persona_id == persona_id):
                    timestamp = task.last_run.isoformat() if task.last_run else ""
                    events.append({
                        "id": f"task-{task.id}-{timestamp}",
                        "type": "task_executed",
                        "timestamp": timestamp,
                        "title": f"执行任务: {task.name}",
                        "description": "成功" if task.last_status == "success" else f"失败: {task.last_error}",
                        "persona_id": task.persona_id,
                        "metadata": {"task_type": task.task_type, "status": task.last_status},
                    })

    except Exception as e:
        logger.error(f"Failed to build timeline events: {e}")

    # Sort by timestamp descending and limit
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return events[:limit]


@router.get("/timeline")
async def get_timeline(
    persona_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500)
) -> List[Dict[str, Any]]:
    """Get global timeline events."""
    orchestrator = _get_orchestrator()
    return await _build_timeline_events(orchestrator, persona_id=persona_id, limit=limit)


@router.get("/stats")
async def get_global_stats() -> Dict[str, Any]:
    """Get global statistics (optimized)."""
    from avatarfactory.service.app import get_scheduler
    from datetime import timedelta

    orchestrator = _get_orchestrator()
    scheduler = get_scheduler()

    persona_ids = orchestrator.kb.list_personas()
    personas = []
    for pid in persona_ids:
        p = orchestrator.kb.load_persona(pid)
        if p:
            personas.append(p)

    # Collect all content in a single pass per persona
    all_content = []
    published_count = 0
    draft_count = 0
    content_cache: Dict[str, List] = {}  # Cache all content per persona
    published_cache: Dict[str, List] = {}  # Cache published content per persona

    for pid in persona_ids:
        drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
        published = orchestrator.kb.list_content(persona_id=pid, status="published")
        published_ids = {c.id for c in published}

        # Count unique drafts (not in published)
        unique_drafts = [c for c in drafts if c.id not in published_ids]
        draft_count += len(unique_drafts)
        published_count += len(published)

        # Combine for all_content
        persona_content = unique_drafts + list(published)
        all_content.extend(persona_content)
        content_cache[pid] = persona_content
        published_cache[pid] = list(published)  # Cache published for later use

    # Calculate average score from content
    total_score = 0
    score_count = 0
    for content in all_content:
        if content.review_score:
            total_score += content.review_score
            score_count += 1

    # Content by day (last 30 days)
    now = datetime.now()
    content_by_day: Dict[str, int] = {}
    for i in range(29, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        content_by_day[date_str] = 0

    for content in all_content:
        if content.created_at:
            date_str = content.created_at.strftime("%Y-%m-%d")
            if date_str in content_by_day:
                content_by_day[date_str] += 1

    # Build persona stats from cached data (no re-querying needed)
    personas_stats = []
    for pid in persona_ids:
        persona_content = content_cache.get(pid, [])
        published_content = published_cache.get(pid, [])

        # Simple stats without loading reviews (expensive)
        content_by_pillar: Dict[str, int] = {}
        content_by_platform: Dict[str, int] = {}
        p_total_score = 0
        p_score_count = 0

        for content in persona_content:
            pillar = content.pillar or "unknown"
            platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)
            content_by_pillar[pillar] = content_by_pillar.get(pillar, 0) + 1
            content_by_platform[platform] = content_by_platform.get(platform, 0) + 1
            if content.review_score:
                p_total_score += content.review_score
                p_score_count += 1

        personas_stats.append({
            "persona_id": pid,
            "total_content": len(persona_content),
            "published_content": len(published_content),
            "draft_content": len(persona_content) - len(published_content),
            "avg_review_score": round(p_total_score / p_score_count) if p_score_count > 0 else 0,
            "content_by_pillar": content_by_pillar,
            "content_by_platform": content_by_platform,
            "score_distribution": {
                "persona_consistency": 0,
                "platform_fit": 0,
                "compliance": 0,
                "engagement_potential": 0,
            },
        })

    # Count active tasks
    active_tasks = 0
    if scheduler:
        active_tasks = len([t for t in scheduler.list_tasks() if t.enabled])

    return {
        "total_personas": len(personas),
        "total_content": len(all_content),
        "total_published": published_count,
        "total_drafts": draft_count,
        "avg_review_score": round(total_score / score_count) if score_count > 0 else 0,
        "active_tasks": active_tasks,
        "content_by_day": [{"date": date, "count": count} for date, count in content_by_day.items()],
        "personas_stats": personas_stats,
    }
