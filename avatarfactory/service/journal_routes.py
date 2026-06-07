"""
Journal API Routes.

Provides API endpoints for the Avatar Journal (养成记) SSR website.
These endpoints return timeline events and data for blog-style storytelling.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from avatarfactory.service.cache import (
    dashboard_cache,
    timeline_cache,
    stats_cache,
    get_or_set_async,
)

router = APIRouter(prefix="/api/journal", tags=["Journal"])
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
# Timeline Events
# =============================================================================


async def _build_all_events(orchestrator, persona_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Build all timeline events from various sources."""
    from avatarfactory.service.app import get_scheduler

    events: List[Dict[str, Any]] = []

    try:
        # Get personas to process
        if persona_id:
            persona_ids = [persona_id]
        else:
            persona_ids = orchestrator.kb.list_personas()

        # Build persona name map
        persona_names: Dict[str, str] = {}
        for pid in persona_ids:
            try:
                persona = orchestrator.kb.load_persona(pid)
                if persona:
                    persona_names[pid] = persona.identity.name
            except Exception:
                persona_names[pid] = pid

        for pid in persona_ids:
            try:
                # Add persona version events from history
                history = orchestrator.kb.get_persona_history(pid)
                for version in history:
                    timestamp = (
                        version.timestamp.isoformat()
                        if hasattr(version.timestamp, "isoformat")
                        else str(version.timestamp)
                    )
                    event_type = (
                        "persona_created" if version.version == "v1.0" else "persona_updated"
                    )
                    title = (
                        f"人设诞生：{persona_names.get(pid, pid)}"
                        if version.version == "v1.0"
                        else f"人设进化：{persona_names.get(pid, pid)} → {version.version}"
                    )
                    description = (
                        f"原因：{version.reason}"
                        if version.reason
                        else (", ".join(version.changes) if version.changes else "")
                    )

                    events.append(
                        {
                            "id": f"{pid}-{version.version}",
                            "type": event_type,
                            "timestamp": timestamp,
                            "title": title,
                            "description": description,
                            "persona_id": pid,
                            "persona_name": persona_names.get(pid, pid),
                            "metadata": {
                                "version": version.version,
                                "changes": version.changes,
                                "reason": version.reason,
                                "author": version.author,
                            },
                        }
                    )
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
                        platform = (
                            content.platform.value
                            if hasattr(content.platform, "value")
                            else str(content.platform)
                        )
                        events.append(
                            {
                                "id": f"content-{content.id}",
                                "type": "content_created",
                                "timestamp": timestamp,
                                "title": (
                                    f"创作新内容：{content.title[:30]}..."
                                    if len(content.title) > 30
                                    else f"创作新内容：{content.title}"
                                ),
                                "description": f"平台: {platform} | 栏目: {content.pillar}",
                                "persona_id": pid,
                                "persona_name": persona_names.get(pid, pid),
                                "content_id": content.id,
                                "content": content.body,  # Include full content body
                                "metadata": {"platform": platform, "pillar": content.pillar},
                            }
                        )

                for content in published:
                    timestamp = content.created_at.isoformat() if content.created_at else ""
                    platform = (
                        content.platform.value
                        if hasattr(content.platform, "value")
                        else str(content.platform)
                    )
                    events.append(
                        {
                            "id": f"publish-{content.id}",
                            "type": "content_published",
                            "timestamp": timestamp,
                            "title": (
                                f"内容发布：{content.title[:30]}..."
                                if len(content.title) > 30
                                else f"内容发布：{content.title}"
                            ),
                            "description": f"成功发布到 {platform}",
                            "persona_id": pid,
                            "persona_name": persona_names.get(pid, pid),
                            "content_id": content.id,
                            "content": content.body,  # Include full content body
                            "metadata": {"platform": platform, "pillar": content.pillar},
                        }
                    )

                # Add review events
                contents = drafts + published
                for content in contents:
                    review = orchestrator.kb.load_review_report(content.id, pid)
                    if review:
                        timestamp = (
                            review.reviewed_at.isoformat()
                            if hasattr(review.reviewed_at, "isoformat")
                            else str(review.reviewed_at)
                        )
                        events.append(
                            {
                                "id": f"review-{content.id}",
                                "type": "review_completed",
                                "timestamp": timestamp,
                                "title": f"质量评审：{review.overall_score}分",
                                "description": f"内容《{content.title[:20]}》通过质量评审",
                                "persona_id": pid,
                                "persona_name": persona_names.get(pid, pid),
                                "content_id": content.id,
                                "metadata": {"score": review.overall_score},
                            }
                        )
            except Exception as e:
                logger.warning(f"Failed to load content/reviews for persona {pid}: {e}")

        # Add task execution events
        scheduler = get_scheduler()
        if scheduler:
            for task in scheduler.list_tasks():
                if task.last_run:
                    if persona_id and task.persona_id != persona_id:
                        continue
                    timestamp = task.last_run.isoformat()
                    success = task.last_status == "success"
                    events.append(
                        {
                            "id": f"task-{task.id}-{timestamp}",
                            "type": "task_executed",
                            "timestamp": timestamp,
                            "title": f"任务执行：{task.name}",
                            "description": (
                                "执行成功" if success else f"执行失败: {task.last_error}"
                            ),
                            "persona_id": task.persona_id,
                            "persona_name": (
                                persona_names.get(task.persona_id, task.persona_id)
                                if task.persona_id
                                else None
                            ),
                            "metadata": {"task_type": task.task_type, "status": task.last_status},
                        }
                    )

    except Exception as e:
        logger.error(f"Failed to build timeline events: {e}")

    # Sort by timestamp descending
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return events


async def _get_cached_events(
    orchestrator, persona_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get timeline events with caching."""
    cache_key = f"events:{persona_id or 'all'}"
    cached = timeline_cache.get(cache_key)
    if cached is not None:
        return cached

    events = await _build_all_events(orchestrator, persona_id)
    timeline_cache.set(cache_key, events)
    return events


@router.get("/events")
async def list_events(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get paginated timeline events."""
    orchestrator = _get_orchestrator()
    all_events = await _get_cached_events(orchestrator)

    total = len(all_events)
    pages = math.ceil(total / limit) if total > 0 else 0
    start = (page - 1) * limit
    end = start + limit

    return {
        "events": all_events[start:end],
        "total": total,
        "page": page,
        "pages": pages,
    }


@router.get("/events/recent")
async def get_recent_events(limit: int = Query(10, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Get most recent events."""
    orchestrator = _get_orchestrator()
    all_events = await _get_cached_events(orchestrator)
    return all_events[:limit]


@router.get("/events/by-type/{event_type}")
async def get_events_by_type(event_type: str) -> List[Dict[str, Any]]:
    """Get events filtered by type."""
    orchestrator = _get_orchestrator()
    all_events = await _get_cached_events(orchestrator)
    return [e for e in all_events if e["type"] == event_type]


@router.get("/events/by-persona/{persona_id}")
async def get_events_by_persona(persona_id: str) -> List[Dict[str, Any]]:
    """Get events for a specific persona."""
    orchestrator = _get_orchestrator()
    return await _get_cached_events(orchestrator, persona_id=persona_id)


@router.get("/events/{event_id}")
async def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    """Get a single event by ID."""
    orchestrator = _get_orchestrator()
    all_events = await _get_cached_events(orchestrator)

    for event in all_events:
        if event["id"] == event_id:
            return event

    return None


# =============================================================================
# Personas (Summary)
# =============================================================================


@router.get("/personas")
async def list_personas() -> List[Dict[str, Any]]:
    """Get all personas with summary info."""
    orchestrator = _get_orchestrator()
    persona_ids = orchestrator.kb.list_personas()
    personas = []

    for pid in persona_ids:
        try:
            persona = orchestrator.kb.load_persona(pid)
            if persona:
                # Count content
                drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
                published = orchestrator.kb.list_content(persona_id=pid, status="published")
                published_ids = {c.id for c in published}
                content_count = len(published) + len(
                    [d for d in drafts if d.id not in published_ids]
                )

                personas.append(
                    {
                        "id": persona.id,
                        "name": persona.identity.name,
                        "tagline": persona.identity.tagline,
                        "expertise": persona.identity.expertise,
                        "content_count": content_count,
                        "created_at": (
                            persona.created_at.isoformat() if persona.created_at else None
                        ),
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load persona {pid}: {e}")

    return personas


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str) -> Optional[Dict[str, Any]]:
    """Get a single persona summary by ID."""
    orchestrator = _get_orchestrator()
    persona = orchestrator.kb.load_persona(persona_id)

    if not persona:
        return None

    # Count content
    drafts = orchestrator.kb.list_content(persona_id=persona_id, status="draft")
    published = orchestrator.kb.list_content(persona_id=persona_id, status="published")
    published_ids = {c.id for c in published}
    content_count = len(published) + len([d for d in drafts if d.id not in published_ids])

    return {
        "id": persona.id,
        "name": persona.identity.name,
        "tagline": persona.identity.tagline,
        "expertise": persona.identity.expertise,
        "content_count": content_count,
        "created_at": persona.created_at.isoformat() if persona.created_at else None,
    }


# =============================================================================
# Content (Summary)
# =============================================================================


@router.get("/content/recent")
async def get_recent_content(limit: int = Query(5, ge=1, le=50)) -> List[Dict[str, Any]]:
    """Get recently published content."""
    orchestrator = _get_orchestrator()
    persona_ids = orchestrator.kb.list_personas()

    # Build persona name map
    persona_names: Dict[str, str] = {}
    for pid in persona_ids:
        try:
            persona = orchestrator.kb.load_persona(pid)
            if persona:
                persona_names[pid] = persona.identity.name
        except Exception:
            persona_names[pid] = pid

    all_content = []
    for pid in persona_ids:
        try:
            published = orchestrator.kb.list_content(persona_id=pid, status="published")
            for content in published:
                platform = (
                    content.platform.value
                    if hasattr(content.platform, "value")
                    else str(content.platform)
                )
                all_content.append(
                    {
                        "id": content.id,
                        "persona_id": pid,
                        "persona_name": persona_names.get(pid, pid),
                        "title": content.title,
                        "body": (
                            content.body[:200] + "..." if len(content.body) > 200 else content.body
                        ),
                        "pillar": content.pillar,
                        "platform": platform,
                        "status": "published",
                        "created_at": (
                            content.created_at.isoformat() if content.created_at else None
                        ),
                        "review_score": content.review_score,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load content for persona {pid}: {e}")

    # Sort by created_at descending
    all_content.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return all_content[:limit]


@router.get("/content/{content_id}")
async def get_content(content_id: str) -> Optional[Dict[str, Any]]:
    """Get a single content item by ID."""
    orchestrator = _get_orchestrator()

    # Try published first
    content = orchestrator.kb.load_content(content_id, status="published")
    content_status = "published"

    if not content:
        content = orchestrator.kb.load_content(content_id, status="draft")
        content_status = "draft"

    if not content:
        return None

    # Get persona name
    persona_name = content.persona_id
    try:
        persona = orchestrator.kb.load_persona(content.persona_id)
        if persona:
            persona_name = persona.identity.name
    except Exception:
        pass

    platform = (
        content.platform.value if hasattr(content.platform, "value") else str(content.platform)
    )

    return {
        "id": content.id,
        "persona_id": content.persona_id,
        "persona_name": persona_name,
        "title": content.title,
        "body": content.body,
        "pillar": content.pillar,
        "platform": platform,
        "status": content_status,
        "created_at": content.created_at.isoformat() if content.created_at else None,
        "review_score": content.review_score,
    }


# =============================================================================
# Stats
# =============================================================================


@router.get("/stats")
async def get_journal_stats() -> Dict[str, Any]:
    """Get journal statistics (cached)."""
    # Try cache first
    cache_key = "journal:stats"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached

    orchestrator = _get_orchestrator()
    persona_ids = orchestrator.kb.list_personas()

    # Count content
    total_content = 0
    published_count = 0
    for pid in persona_ids:
        try:
            drafts = orchestrator.kb.list_content(persona_id=pid, status="draft")
            published = orchestrator.kb.list_content(persona_id=pid, status="published")
            published_ids = {c.id for c in published}
            total_content += len(published) + len([d for d in drafts if d.id not in published_ids])
            published_count += len(published)
        except Exception:
            pass

    # Use cached events
    all_events = await _get_cached_events(orchestrator)
    events_by_type: Dict[str, int] = {}
    for event in all_events:
        event_type = event["type"]
        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

    # Events by day (last 30 days)
    events_by_day: Dict[str, int] = {}
    now = datetime.now()
    for i in range(29, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        events_by_day[date_str] = 0

    for event in all_events:
        if event.get("timestamp"):
            try:
                event_date = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                date_str = event_date.strftime("%Y-%m-%d")
                if date_str in events_by_day:
                    events_by_day[date_str] += 1
            except Exception:
                pass

    result = {
        "total_events": len(all_events),
        "total_personas": len(persona_ids),
        "total_content": total_content,
        "total_published": published_count,
        "events_by_type": events_by_type,
        "events_by_day": [{"date": date, "count": count} for date, count in events_by_day.items()],
    }

    # Cache the result
    stats_cache.set(cache_key, result)
    return result


# =============================================================================
# Dashboard Endpoint (Optimized - Single API call)
# =============================================================================


@router.get("/dashboard")
async def get_journal_dashboard() -> Dict[str, Any]:
    """
    Get all journal dashboard data in a single API call.

    Returns events, stats, and recent content optimized for the homepage.
    Uses caching to reduce repeated computation (30 second TTL).
    """
    cache_key = "journal_dashboard"

    async def build_dashboard():
        orchestrator = _get_orchestrator()

        # Use batch loading for stats
        batch_stats = orchestrator.kb.get_batch_persona_stats()
        persona_summaries = orchestrator.kb.list_personas_summary()

        # Calculate totals from batch stats
        total_content = sum(s.get("total_content", 0) for s in batch_stats.values())
        total_published = sum(s.get("published_content", 0) for s in batch_stats.values())

        # Build events using cached/optimized method
        all_events = await _build_all_events_optimized(orchestrator)

        # Count events by type
        events_by_type: Dict[str, int] = {}
        for event in all_events:
            event_type = event["type"]
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

        # Events by day (last 30 days)
        now = datetime.now()
        events_by_day: Dict[str, int] = {}
        for i in range(29, -1, -1):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            events_by_day[date_str] = 0

        for event in all_events:
            if event.get("timestamp"):
                try:
                    event_date = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                    date_str = event_date.strftime("%Y-%m-%d")
                    if date_str in events_by_day:
                        events_by_day[date_str] += 1
                except Exception:
                    pass

        stats = {
            "total_events": len(all_events),
            "total_personas": len(persona_summaries),
            "total_content": total_content,
            "total_published": total_published,
            "events_by_type": events_by_type,
            "events_by_day": [
                {"date": date, "count": count} for date, count in events_by_day.items()
            ],
        }

        return {
            "events": all_events[:50],  # Limit to 50 events
            "stats": stats,
        }

    return await get_or_set_async(dashboard_cache, cache_key, build_dashboard)


async def _build_all_events_optimized(
    orchestrator, persona_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Build all timeline events using batch loading for better performance.

    Uses batch review loading to avoid N+1 queries.
    """
    from avatarfactory.service.app import get_scheduler

    events: List[Dict[str, Any]] = []

    try:
        # Get personas to process
        if persona_id:
            persona_ids = [persona_id]
        else:
            persona_ids = orchestrator.kb.list_personas()

        # Build persona name map using batch loading
        persona_names: Dict[str, str] = {}
        persona_summaries = orchestrator.kb.list_personas_summary()
        for summary in persona_summaries:
            persona_names[summary["id"]] = summary["name"]

        # Batch load all reviews
        all_reviews = orchestrator.kb.get_all_reviews_batch(persona_id)

        for pid in persona_ids:
            try:
                # Add persona version events from history
                history = orchestrator.kb.get_persona_history(pid)
                for version in history:
                    timestamp = (
                        version.timestamp.isoformat()
                        if hasattr(version.timestamp, "isoformat")
                        else str(version.timestamp)
                    )
                    event_type = (
                        "persona_created" if version.version == "v1.0" else "persona_updated"
                    )
                    title = (
                        f"人设诞生：{persona_names.get(pid, pid)}"
                        if version.version == "v1.0"
                        else f"人设进化：{persona_names.get(pid, pid)} → {version.version}"
                    )
                    description = (
                        f"原因：{version.reason}"
                        if version.reason
                        else (", ".join(version.changes) if version.changes else "")
                    )

                    events.append(
                        {
                            "id": f"{pid}-{version.version}",
                            "type": event_type,
                            "timestamp": timestamp,
                            "title": title,
                            "description": description,
                            "persona_id": pid,
                            "persona_name": persona_names.get(pid, pid),
                            "metadata": {
                                "version": version.version,
                                "changes": version.changes,
                                "reason": version.reason,
                                "author": version.author,
                            },
                        }
                    )
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
                        platform = (
                            content.platform.value
                            if hasattr(content.platform, "value")
                            else str(content.platform)
                        )
                        events.append(
                            {
                                "id": f"content-{content.id}",
                                "type": "content_created",
                                "timestamp": timestamp,
                                "title": (
                                    f"创作新内容：{content.title[:30]}..."
                                    if len(content.title) > 30
                                    else f"创作新内容：{content.title}"
                                ),
                                "description": f"平台: {platform} | 栏目: {content.pillar}",
                                "persona_id": pid,
                                "persona_name": persona_names.get(pid, pid),
                                "content_id": content.id,
                                "content": content.body,
                                "metadata": {"platform": platform, "pillar": content.pillar},
                            }
                        )

                for content in published:
                    timestamp = content.created_at.isoformat() if content.created_at else ""
                    platform = (
                        content.platform.value
                        if hasattr(content.platform, "value")
                        else str(content.platform)
                    )
                    events.append(
                        {
                            "id": f"publish-{content.id}",
                            "type": "content_published",
                            "timestamp": timestamp,
                            "title": (
                                f"内容发布：{content.title[:30]}..."
                                if len(content.title) > 30
                                else f"内容发布：{content.title}"
                            ),
                            "description": f"成功发布到 {platform}",
                            "persona_id": pid,
                            "persona_name": persona_names.get(pid, pid),
                            "content_id": content.id,
                            "content": content.body,
                            "metadata": {"platform": platform, "pillar": content.pillar},
                        }
                    )

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
                        events.append(
                            {
                                "id": f"review-{content.id}",
                                "type": "review_completed",
                                "timestamp": timestamp,
                                "title": f"质量评审：{review.get('overall_score', 0)}分",
                                "description": f"内容《{content.title[:20]}》通过质量评审",
                                "persona_id": pid,
                                "persona_name": persona_names.get(pid, pid),
                                "content_id": content.id,
                                "metadata": {"score": review.get("overall_score", 0)},
                            }
                        )
            except Exception as e:
                logger.warning(f"Failed to load content/reviews for persona {pid}: {e}")

        # Add task execution events
        scheduler = get_scheduler()
        if scheduler:
            for task in scheduler.list_tasks():
                if task.last_run:
                    if persona_id and task.persona_id != persona_id:
                        continue
                    timestamp = task.last_run.isoformat()
                    success = task.last_status == "success"
                    events.append(
                        {
                            "id": f"task-{task.id}-{timestamp}",
                            "type": "task_executed",
                            "timestamp": timestamp,
                            "title": f"任务执行：{task.name}",
                            "description": (
                                "执行成功" if success else f"执行失败: {task.last_error}"
                            ),
                            "persona_id": task.persona_id,
                            "persona_name": (
                                persona_names.get(task.persona_id, task.persona_id)
                                if task.persona_id
                                else None
                            ),
                            "metadata": {"task_type": task.task_type, "status": task.last_status},
                        }
                    )

    except Exception as e:
        logger.error(f"Failed to build timeline events: {e}")

    # Sort by timestamp descending
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return events
