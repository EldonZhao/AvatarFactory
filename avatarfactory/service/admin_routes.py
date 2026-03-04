"""
Admin API routes for Avatar Admin dashboard.

Provides aggregated endpoints for the admin dashboard UI.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/admin", tags=["Admin"])


# =============================================================================
# Authentication Dependency
# =============================================================================


async def require_admin_auth(admin_token: Optional[str] = Cookie(None)) -> dict:
    """
    Dependency to require admin authentication.

    Returns the current user info if authenticated, raises 401 otherwise.
    """
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    from avatarfactory.service.auth_routes import verify_token

    payload = verify_token(admin_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {"username": payload.get("sub", "")}


# =============================================================================
# Response Models
# =============================================================================


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response."""
    personas_count: int
    contents_count: int
    draft_count: int
    published_count: int
    tasks_count: int
    active_tasks_count: int
    connectors_configured: int
    connectors_total: int


class PersonaSummary(BaseModel):
    """Persona summary for dashboard."""
    id: str
    name: str
    tagline: str
    platforms: List[str]
    content_count: int
    draft_count: int
    version: str


class ConnectorStatusResponse(BaseModel):
    """Connector status for dashboard."""
    platform: str
    registered: bool
    configured: bool
    description: str


class DashboardResponse(BaseModel):
    """Full dashboard data response."""
    stats: DashboardStatsResponse
    recent_personas: List[PersonaSummary]
    connectors: List[ConnectorStatusResponse]
    scheduler_running: bool
    next_task_run: Optional[str] = None


# =============================================================================
# Helper functions
# =============================================================================


def get_orchestrator():
    """Get the orchestrator instance."""
    from avatarfactory.service.app import _orchestrator
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized",
        )
    return _orchestrator


def get_scheduler():
    """Get the scheduler instance."""
    from avatarfactory.service.app import _scheduler
    return _scheduler


# =============================================================================
# Dashboard endpoints
# =============================================================================


@router.get("/dashboard", response_model=DashboardResponse, dependencies=[Depends(require_admin_auth)])
async def get_dashboard():
    """
    Get dashboard overview data.

    Returns aggregated statistics, recent personas, connector status,
    and scheduler information.
    """
    import os
    from avatarfactory.connectors.registry import ConnectorRegistry

    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    # Count personas
    persona_ids = kb.list_personas()
    personas_count = len(persona_ids)

    # Count content
    draft_contents = kb.list_content(status="draft")
    published_contents = kb.list_content(status="published")
    draft_count = len(draft_contents)
    published_count = len(published_contents)
    contents_count = draft_count + published_count

    # Count tasks
    tasks = scheduler.list_tasks() if scheduler else []
    tasks_count = len(tasks)
    active_tasks_count = sum(1 for t in tasks if t.enabled)

    # Build recent personas list
    recent_personas = []
    for pid in persona_ids[:5]:  # Show last 5
        persona = kb.load_persona(pid)
        if persona:
            p_draft = len(kb.list_content(persona_id=pid, status="draft"))
            p_published = len(kb.list_content(persona_id=pid, status="published"))
            recent_personas.append(PersonaSummary(
                id=persona.id,
                name=persona.identity.name,
                tagline=persona.identity.tagline,
                platforms=[pt.value for pt in persona.platforms],
                content_count=p_draft + p_published,
                draft_count=p_draft,
                version=persona.version,
            ))

    # Get connector status
    connector_configs = {
        "bluesky": {
            "env_keys": ["BLUESKY_USERNAME", "BLUESKY_PASSWORD"],
            "description": "AT Protocol social network",
        },
        "twitter": {
            "env_keys": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN"],
            "description": "Twitter/X API v2",
        },
        "xiaohongshu": {
            "env_keys": ["XIAOHONGSHU_COOKIE"],
            "description": "Little Red Book (小红书)",
        },
        "wecom": {
            "env_keys": ["AVATARFACTORY_WEBHOOK_URL"],
            "description": "WeChat Work notifications",
        },
        "linkedin": {
            "env_keys": ["LINKEDIN_ACCESS_TOKEN"],
            "description": "LinkedIn OAuth 2.0",
        },
    }

    connectors = []
    connectors_configured = 0
    for platform, config in connector_configs.items():
        registered = ConnectorRegistry.is_registered(platform)
        configured = all(os.getenv(k) is not None for k in config["env_keys"])
        if configured:
            connectors_configured += 1
        connectors.append(ConnectorStatusResponse(
            platform=platform,
            registered=registered,
            configured=configured,
            description=config["description"],
        ))

    # Scheduler status
    scheduler_running = scheduler.is_running() if scheduler else False
    next_runs = scheduler.get_next_runs() if scheduler else []
    next_task_run = next_runs[0].get("next_run") if next_runs else None

    return DashboardResponse(
        stats=DashboardStatsResponse(
            personas_count=personas_count,
            contents_count=contents_count,
            draft_count=draft_count,
            published_count=published_count,
            tasks_count=tasks_count,
            active_tasks_count=active_tasks_count,
            connectors_configured=connectors_configured,
            connectors_total=len(connector_configs),
        ),
        recent_personas=recent_personas,
        connectors=connectors,
        scheduler_running=scheduler_running,
        next_task_run=next_task_run,
    )


@router.get("/personas", dependencies=[Depends(require_admin_auth)])
async def list_personas_admin():
    """
    List all personas with extended info for admin.
    """
    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    persona_ids = kb.list_personas()
    personas = []

    for pid in persona_ids:
        persona = kb.load_persona(pid)
        if persona:
            draft_count = len(kb.list_content(persona_id=pid, status="draft"))
            published_count = len(kb.list_content(persona_id=pid, status="published"))

            # Get tasks for this persona
            persona_tasks = [t for t in (scheduler.list_tasks() if scheduler else [])
                           if t.persona_id == pid]

            personas.append({
                "id": persona.id,
                "name": persona.identity.name,
                "tagline": persona.identity.tagline,
                "platforms": [pt.value for pt in persona.platforms],
                "expertise": persona.identity.expertise,
                "version": persona.version,
                "content_count": draft_count + published_count,
                "draft_count": draft_count,
                "published_count": published_count,
                "tasks_count": len(persona_tasks),
                "notification_enabled": persona.notification.enabled if persona.notification else False,
                "created_at": persona.created_at.isoformat() if persona.created_at else None,
                "updated_at": persona.updated_at.isoformat() if persona.updated_at else None,
            })

    return {
        "count": len(personas),
        "personas": personas,
    }


@router.get("/personas/{persona_id}", dependencies=[Depends(require_admin_auth)])
async def get_persona_admin(persona_id: str):
    """Get persona detail for admin."""
    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    persona = kb.load_persona(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {persona_id} not found",
        )

    # Get content counts
    draft_count = len(kb.list_content(persona_id=persona_id, status="draft"))
    published_count = len(kb.list_content(persona_id=persona_id, status="published"))

    # Get tasks
    persona_tasks = [t for t in (scheduler.list_tasks() if scheduler else [])
                    if t.persona_id == persona_id]

    # Get version history
    versions = kb.list_persona_versions(persona_id)

    return {
        **persona.model_dump(mode="json"),
        "content_count": draft_count + published_count,
        "draft_count": draft_count,
        "published_count": published_count,
        "tasks": [{
            "id": t.id,
            "name": t.name,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "enabled": t.enabled,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "last_status": t.last_status,
        } for t in persona_tasks],
        "versions": versions,
    }


@router.get("/content", dependencies=[Depends(require_admin_auth)])
async def list_content_admin(
    persona_id: Optional[str] = None,
    content_status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
):
    """
    List content items with filtering for admin.
    """
    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    # Build content list from both drafts and published
    all_contents = []

    statuses = [content_status] if content_status else ["draft", "published"]

    for s in statuses:
        contents = kb.list_content(persona_id=persona_id, status=s)
        for c in contents:
            # Filter by platform if specified
            if platform and c.platform.value != platform:
                continue

            all_contents.append({
                "id": c.id,
                "title": c.title,
                "persona_id": c.persona_id,
                "platform": c.platform.value,
                "pillar": c.pillar,
                "status": s,
                "review_score": c.review_score,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

    # Sort by created_at descending
    all_contents.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    return {
        "count": len(all_contents[:limit]),
        "total": len(all_contents),
        "content": all_contents[:limit],
    }


@router.get("/content/{content_id}", dependencies=[Depends(require_admin_auth)])
async def get_content_admin(content_id: str):
    """Get content detail for admin."""
    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    # Try loading from draft first, then published
    content = kb.load_content(content_id, status="draft")
    content_status = "draft"
    if not content:
        content = kb.load_content(content_id, status="published")
        content_status = "published"

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {content_id} not found",
        )

    # Get persona name
    persona = kb.load_persona(content.persona_id)
    persona_name = persona.identity.name if persona else content.persona_id

    return {
        "id": content.id,
        "title": content.title,
        "body": content.body,
        "tags": content.tags,
        "persona_id": content.persona_id,
        "persona_name": persona_name,
        "platform": content.platform.value,
        "pillar": content.pillar,
        "status": content_status,
        "review_score": content.review_score,
        "review_issues": content.review_issues,
        "review_details": content.review_details.model_dump() if content.review_details else None,
        "created_at": content.created_at.isoformat() if content.created_at else None,
        "metadata": content.metadata,
        "media": [m.model_dump() for m in content.media] if content.media else [],
        "image_prompts": content.image_prompts,
    }


@router.delete("/content/{content_id}", dependencies=[Depends(require_admin_auth)])
async def delete_content_admin(content_id: str):
    """Delete a content item."""
    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    # Try to find and delete from both statuses
    deleted = False
    for s in ["draft", "published"]:
        content = kb.load_content(content_id, status=s)
        if content:
            kb.delete_content(content_id, status=s)
            deleted = True
            break

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {content_id} not found",
        )

    return {"status": "deleted", "content_id": content_id}


@router.get("/scheduler/tasks", dependencies=[Depends(require_admin_auth)])
async def list_scheduler_tasks_admin():
    """List all scheduler tasks grouped by persona."""
    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    if not scheduler:
        return {"tasks": [], "grouped": {}}

    tasks = scheduler.list_tasks()

    # Group by persona
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for t in tasks:
        task_data = {
            "id": t.id,
            "name": t.name,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "platform": t.platform,
            "enabled": t.enabled,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "last_status": t.last_status,
            "last_error": t.last_error,
            "run_count": t.run_count,
        }

        persona_id = t.persona_id or "system"
        if persona_id not in grouped:
            grouped[persona_id] = []
        grouped[persona_id].append(task_data)

    # Add persona names
    result = {}
    for pid, task_list in grouped.items():
        if pid == "system":
            result["system"] = {
                "persona_name": "System Tasks",
                "tasks": task_list,
            }
        else:
            persona = kb.load_persona(pid)
            result[pid] = {
                "persona_name": persona.identity.name if persona else pid,
                "tasks": task_list,
            }

    return {
        "count": len(tasks),
        "grouped": result,
    }


@router.get("/topics", dependencies=[Depends(require_admin_auth)])
async def list_topics_admin(
    persona_id: Optional[str] = None,
    limit: int = 50,
):
    """List discovered topics/ideas grouped by persona."""
    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    persona_ids = [persona_id] if persona_id else kb.list_personas()

    all_topics = []
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for pid in persona_ids:
        discoveries = kb.list_discoveries(pid)
        persona = kb.load_persona(pid)
        persona_name = persona.identity.name if persona else pid

        if pid not in grouped:
            grouped[pid] = {
                "persona_name": persona_name,
                "topics": [],
            }

        for d in discoveries[:limit]:
            topic_data = {
                "id": d.id,
                "platform": d.platform.value if hasattr(d.platform, "value") else str(d.platform),
                "topics": d.topics[:5] if d.topics else [],
                "ideas": d.content_ideas[:3] if d.content_ideas else [],
                "discovered_at": d.timestamp.isoformat() if d.timestamp else None,
            }
            grouped[pid]["topics"].append(topic_data)
            all_topics.append({**topic_data, "persona_id": pid, "persona_name": persona_name})

    return {
        "count": len(all_topics),
        "grouped": grouped,
        "topics": all_topics[:limit],
    }


@router.get("/connectors", dependencies=[Depends(require_admin_auth)])
async def list_connectors_admin():
    """Get detailed connector status for admin."""
    import os
    from avatarfactory.connectors.registry import ConnectorRegistry

    connector_configs = {
        "bluesky": {
            "env_keys": ["BLUESKY_USERNAME", "BLUESKY_PASSWORD"],
            "description": "AT Protocol social network",
        },
        "twitter": {
            "env_keys": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"],
            "description": "Twitter/X API v2",
        },
        "xiaohongshu": {
            "env_keys": ["XIAOHONGSHU_COOKIE", "XIAOHONGSHU_USER_ID"],
            "description": "Little Red Book (小红书)",
        },
        "wecom": {
            "env_keys": ["AVATARFACTORY_WEBHOOK_URL"],
            "description": "WeChat Work notifications",
        },
        "linkedin": {
            "env_keys": ["LINKEDIN_ACCESS_TOKEN"],
            "description": "LinkedIn OAuth 2.0",
        },
        "threads": {
            "env_keys": ["THREADS_ACCESS_TOKEN"],
            "description": "Threads (Meta) Graph API",
        },
        "instagram": {
            "env_keys": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID"],
            "description": "Instagram Business Graph API",
        },
        "weibo": {
            "env_keys": ["WEIBO_ACCESS_TOKEN"],
            "description": "Weibo (微博) OAuth 2.0",
        },
        "mastodon": {
            "env_keys": ["MASTODON_ACCESS_TOKEN", "MASTODON_INSTANCE_URL"],
            "description": "Mastodon/Fediverse",
        },
    }

    connectors = []
    for platform, config in connector_configs.items():
        registered = ConnectorRegistry.is_registered(platform)
        configured_keys = [(k, os.getenv(k) is not None) for k in config["env_keys"]]
        all_configured = all(v for _, v in configured_keys)

        connectors.append({
            "platform": platform,
            "description": config["description"],
            "registered": registered,
            "configured": all_configured,
            "env_keys": [{
                "key": k,
                "configured": v,
            } for k, v in configured_keys],
        })

    return {
        "connectors": connectors,
        "configured_count": sum(1 for c in connectors if c["configured"]),
        "total_count": len(connectors),
    }
