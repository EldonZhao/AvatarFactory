"""
Admin API routes for Avatar Admin dashboard.

Provides aggregated endpoints for the admin dashboard UI.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, status
from pydantic import BaseModel, Field

from avatarfactory.service.cache import persona_cache, stats_cache


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
    model_info: Optional[str] = None


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
                content_count=p_draft + p_published,
                draft_count=p_draft,
                version=persona.version,
            ))

    # Get connector status
    all_capabilities = ConnectorRegistry.get_all_capabilities()

    connectors = []
    connectors_configured = 0
    for platform, caps in all_capabilities.items():
        env_keys = [f.env_var for f in caps.config_fields if f.env_var]
        configured = all(os.getenv(k) is not None for k in env_keys) if env_keys else False
        if configured:
            connectors_configured += 1
        connectors.append(ConnectorStatusResponse(
            platform=caps.platform,
            registered=True,
            configured=configured,
            description=caps.description,
        ))

    # Scheduler status
    scheduler_running = scheduler.is_running() if scheduler else False
    next_runs = scheduler.get_next_runs() if scheduler else []
    next_task_run = next_runs[0].get("next_run") if next_runs else None

    # Model info
    model = os.getenv("AVATARFACTORY_MODEL", "")
    provider = os.getenv("AVATARFACTORY_LLM_PROVIDER", "")
    model_info = f"{provider}/{model}" if provider and model else (model or provider or None)

    return DashboardResponse(
        stats=DashboardStatsResponse(
            personas_count=personas_count,
            contents_count=contents_count,
            draft_count=draft_count,
            published_count=published_count,
            tasks_count=tasks_count,
            active_tasks_count=active_tasks_count,
            connectors_configured=connectors_configured,
            connectors_total=len(all_capabilities),
        ),
        recent_personas=recent_personas,
        connectors=connectors,
        scheduler_running=scheduler_running,
        next_task_run=next_task_run,
        model_info=model_info,
    )


# =============================================================================
# Create Persona Request Model
# =============================================================================


class CreatePersonaRequest(BaseModel):
    """Request to create a new persona."""
    name: str = Field(..., description="Persona name")
    tagline: Optional[str] = Field(None, description="Short tagline")
    description: str = Field(..., description="Persona description")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")


@router.post("/personas", dependencies=[Depends(require_admin_auth)])
async def create_persona_admin(request: CreatePersonaRequest):
    """
    Create a new persona via Admin dashboard.
    """
    import uuid
    from datetime import datetime
    from avatarfactory.models.schemas import (
        Persona,
        Identity,
        VoiceStyle,
        TargetAudience,
        Boundaries,
        PlatformType,
    )
    from avatarfactory.service.cache import invalidate_persona_caches

    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    # Generate persona ID
    persona_id = f"persona_{uuid.uuid4().hex[:8]}"

    # Create persona with defaults
    tagline = request.tagline or ""
    if not tagline and request.description:
        tagline = request.description[:50]

    persona = Persona(
        id=persona_id,
        identity=Identity(
            name=request.name,
            tagline=tagline,
            expertise=request.expertise if request.expertise else [],
        ),
        target_audience=TargetAudience(
            primary="通用受众",
            pain_points=[],
            goals=[],
        ),
        voice_style=VoiceStyle(
            tone="informative",
            language_patterns=[],
            emoji_usage="moderate",
        ),
        content_pillars=[],
        boundaries=Boundaries(
            avoid=[],
            compliance=[],
        ),
        version="v1.0",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Save persona
    kb.save_persona(persona)

    # Invalidate cache
    invalidate_persona_caches()

    return {
        "id": persona.id,
        "name": persona.identity.name,
        "status": "created",
    }


@router.get("/personas", dependencies=[Depends(require_admin_auth)])
async def list_personas_admin():
    """
    List all personas with extended info for admin.
    Uses batch methods to minimize file I/O.
    """
    # Try to get from cache first
    cache_key = "admin:personas:list"
    cached = persona_cache.get(cache_key)
    if cached is not None:
        return cached

    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    # Use batch loading for summaries and stats
    summaries = kb.list_personas_summary()
    persona_ids = [s["id"] for s in summaries]
    batch_stats = kb.get_batch_persona_stats(persona_ids)

    # Build task counts map (scheduler tasks are small, OK to iterate)
    all_tasks = scheduler.list_tasks() if scheduler else []
    task_counts: Dict[str, int] = {}
    for task in all_tasks:
        if task.persona_id:
            task_counts[task.persona_id] = task_counts.get(task.persona_id, 0) + 1

    personas = []
    for summary in summaries:
        pid = summary["id"]
        stats = batch_stats.get(pid, {})

        # For notification enabled, we need to load persona (lightweight check)
        # TODO: Add notification to summary in future optimization
        persona = kb.load_persona(pid)
        notification_enabled = (
            persona.notification.enabled if persona and persona.notification else False
        )

        personas.append({
            "id": pid,
            "name": summary.get("name", ""),
            "tagline": summary.get("tagline", ""),
            "expertise": summary.get("expertise", []),
            "version": summary.get("version", "v1.0"),
            "content_count": stats.get("total_content", 0),
            "draft_count": stats.get("draft_content", 0),
            "published_count": stats.get("published_content", 0),
            "tasks_count": task_counts.get(pid, 0),
            "notification_enabled": notification_enabled,
            "created_at": summary.get("created_at"),
            "updated_at": summary.get("updated_at"),
        })

    result = {
        "count": len(personas),
        "personas": personas,
    }

    # Cache the result
    persona_cache.set(cache_key, result)
    return result


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


class UpdateNotificationRequest(BaseModel):
    """Request to update persona notification settings."""
    enabled: bool = Field(..., description="Enable notifications")
    notify_on_content: bool = Field(default=True, description="Notify on content generation")
    notify_on_discovery: bool = Field(default=True, description="Notify on discovery completion")
    notify_on_review: bool = Field(default=True, description="Notify on review completion")


@router.put("/personas/{persona_id}/notification", dependencies=[Depends(require_admin_auth)])
async def update_persona_notification(persona_id: str, request: UpdateNotificationRequest):
    """
    Update persona notification settings.

    Enables/disables webhook notifications for content generation, discovery, etc.
    """
    from datetime import datetime

    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    persona = kb.load_persona(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {persona_id} not found",
        )

    # Update notification settings
    from avatarfactory.models.schemas import NotificationConfig

    persona.notification = NotificationConfig(
        enabled=request.enabled,
        notify_on_content=request.notify_on_content,
        notify_on_discovery=request.notify_on_discovery,
        notify_on_review=request.notify_on_review,
    )
    persona.updated_at = datetime.now()

    # Save persona
    kb.save_persona(persona)

    return {
        "status": "updated",
        "persona_id": persona_id,
        "notification": persona.notification.model_dump(),
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
    # Try to get from cache first (using filter params as key)
    cache_key = f"admin:content:{persona_id or 'all'}:{content_status or 'all'}:{platform or 'all'}:{limit}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached

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

    result = {
        "count": len(all_contents[:limit]),
        "total": len(all_contents),
        "content": all_contents[:limit],
    }

    # Cache the result
    stats_cache.set(cache_key, result)
    return result


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

    # Load review report for detailed scores
    review_details = None
    try:
        review = kb.load_review_report(content_id, content.persona_id)
        if review:
            review_details = {
                "persona_consistency": review.persona_consistency.score,
                "platform_fit": review.platform_fit.score,
                "compliance": review.compliance.score,
                "engagement_potential": review.engagement_potential.score,
            }
    except Exception:
        pass  # Review report may not exist

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
        "review_details": review_details,
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


# =============================================================================
# Content Generation Request Model
# =============================================================================


class GenerateContentAdminRequest(BaseModel):
    """Content generation request for admin dashboard."""
    persona_id: str = Field(..., description="Persona ID")
    topic: Optional[str] = Field(None, description="Content topic")
    platform: Optional[str] = Field(None, description="Target platform")
    content_type: Optional[str] = Field(None, description="Content type/template")
    instructions: Optional[str] = Field(None, description="Additional instructions")


@router.post("/content/generate", dependencies=[Depends(require_admin_auth)])
async def generate_content_admin(request: GenerateContentAdminRequest):
    """
    Generate content for a persona via Admin dashboard.

    This endpoint wraps the main content generation API and adds notification support.
    """
    import os
    import httpx
    import logging

    logger = logging.getLogger("avatarfactory.service.admin")

    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    # Verify persona exists
    persona = kb.load_persona(request.persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {request.persona_id} not found",
        )

    # Determine pillar (use first content pillar or default)
    pillar = "General"
    if persona.content_pillars:
        pillar = persona.content_pillars[0].name

    from avatarfactory.models.schemas import AgentMessage, TaskType

    message = AgentMessage(
        sender="admin_api",
        receiver="content",
        task_type=TaskType.GENERATE_CONTENT,
        payload={
            "persona_id": request.persona_id,
            "pillar": pillar,
            "topic": request.topic or request.instructions or "latest trends",
            "template": request.content_type or "comparison",
            "use_trending": True,
            "variant_count": 1,
        },
        context={},
    )

    try:
        content = await orchestrator.content_agent.process(message)

        # Send webhook notification
        await _send_admin_content_notification(
            persona=persona,
            content_id=content.id,
            content_title=content.title,
            content_body=content.body,
            review_score=content.review_score,
            platform=content.platform.value,
        )

        return {
            "id": content.id,
            "title": content.title,
            "body": content.body,
            "tags": content.tags,
            "platform": content.platform.value,
            "review_score": content.review_score,
            "persona_id": request.persona_id,
        }
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


async def _send_admin_content_notification(
    persona: Any,
    content_id: str,
    content_title: str,
    content_body: str,
    review_score: Optional[int],
    platform: str,
) -> None:
    """
    Send webhook notification when content is generated via Admin API.
    """
    import os
    import logging
    import httpx

    logger = logging.getLogger("avatarfactory.service.admin")

    # Check if webhook is configured
    webhook_url = os.getenv("AVATARFACTORY_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("No AVATARFACTORY_WEBHOOK_URL configured, skipping notification")
        return

    # Check persona notification settings
    if persona.notification is None or not persona.notification.enabled:
        logger.debug(f"Notifications disabled for persona {persona.id}")
        return

    if not persona.notification.notify_on_content:
        logger.debug(f"Content notifications disabled for persona {persona.id}")
        return

    # Build notification
    persona_name = persona.identity.name if persona.identity else persona.id

    # Build description
    description_parts = []
    if persona_name:
        description_parts.append(f"👤 {persona_name}")
    if platform:
        description_parts.append(f"📱 {platform}")
    if review_score is not None:
        if review_score >= 80:
            description_parts.append(f"✅ 评分: {review_score}/100")
        elif review_score >= 60:
            description_parts.append(f"⚠️ 评分: {review_score}/100")
        else:
            description_parts.append(f"❌ 评分: {review_score}/100")

    # Content preview
    body_preview = content_body[:300] if content_body else ''
    if len(content_body) > 300:
        body_preview += "..."

    if description_parts:
        description = " | ".join(description_parts) + "\n\n" + body_preview
    else:
        description = body_preview

    # Build URL - use Journal public page instead of Admin dashboard
    # This allows viewing content without login
    dashboard_url = os.getenv("AVATARFACTORY_DASHBOARD_URL", "").rstrip("/")
    if not dashboard_url:
        dashboard_url = os.getenv("AVATARFACTORY_SERVICE_URL", "").rstrip("/")

    if dashboard_url and content_id:
        url = f"{dashboard_url}/journal/content/{content_id}"
    else:
        url = ""

    title = f"📝 {content_title}"
    if len(title) > 60:
        title = title[:57] + "..."

    # Build payload
    if not url:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {title}\n\n{description}"
            }
        }
    else:
        payload = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": description[:512],
                        "url": url,
                        "picurl": "",
                    }
                ]
            }
        }

    # Send notification
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("errcode") == 0:
                    logger.info(f"Sent content notification for {content_id}")
                else:
                    logger.warning(f"Content notification failed: {data.get('errmsg')}")
            else:
                logger.warning(f"Content notification HTTP error: {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to send content notification: {e}")


@router.get("/scheduler/tasks", dependencies=[Depends(require_admin_auth)])
async def list_scheduler_tasks_admin():
    """List all scheduler tasks grouped by persona."""
    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    if not scheduler:
        return {"tasks": [], "grouped": {}}

    tasks = scheduler.list_tasks()

    # Get next run times for each task
    next_runs = scheduler.get_next_runs() if scheduler.is_running() else []
    next_run_map = {nr["task_id"]: nr["next_run"] for nr in next_runs}

    # Build flat list and group by persona
    all_tasks = []
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for t in tasks:
        task_data = {
            "id": t.id,
            "name": t.name,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "platform": t.platform,
            "persona_id": t.persona_id,
            "enabled": t.enabled,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "last_status": t.last_status,
            "last_error": t.last_error,
            "run_count": t.run_count,
            "next_run_time": next_run_map.get(t.id),
        }
        all_tasks.append(task_data)

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
        "tasks": all_tasks,
        "grouped": result,
    }


class CreateSchedulerTaskRequest(BaseModel):
    """Request to create a new scheduler task."""
    name: Optional[str] = Field(None, description="Task name (auto-generated if not provided)")
    task_type: str = Field(..., description="Task type (discovery, content, publish)")
    persona_id: str = Field(..., description="Persona ID")
    schedule: str = Field(..., description="Cron schedule expression")
    platform: Optional[str] = Field(None, description="Target platform")
    enabled: bool = Field(default=True, description="Whether task is enabled")


@router.post("/scheduler/tasks", dependencies=[Depends(require_admin_auth)])
async def create_scheduler_task_admin(request: CreateSchedulerTaskRequest):
    """
    Create a new scheduler task via Admin dashboard.
    """
    import uuid

    orchestrator = get_orchestrator()
    kb = orchestrator.kb
    scheduler = get_scheduler()

    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not available",
        )

    # Verify persona exists
    persona = kb.load_persona(request.persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona {request.persona_id} not found",
        )

    # Generate task name if not provided
    task_type_names = {
        "topic": "发现话题",
        "discovery": "发现话题",
        "content": "生成内容",
        "publish": "发布内容",
    }
    task_name = request.name
    if not task_name:
        type_name = task_type_names.get(request.task_type, request.task_type)
        task_name = f"{persona.identity.name} - {type_name}"

    # Generate task ID
    task_id = f"{request.task_type}_{uuid.uuid4().hex[:8]}"

    # Create task via scheduler
    task = scheduler.add_task_from_dict({
        "id": task_id,
        "name": task_name,
        "task_type": request.task_type,
        "schedule": request.schedule,
        "persona_id": request.persona_id,
        "platform": request.platform,
        "enabled": request.enabled,
    })

    return {
        "id": task.id,
        "name": task.name,
        "status": "created",
    }


@router.post("/scheduler/tasks/{task_id}/run", dependencies=[Depends(require_admin_auth)])
async def run_scheduler_task_admin(task_id: str, background_tasks: BackgroundTasks):
    """
    Run a scheduled task immediately via Admin dashboard.
    """
    from datetime import datetime

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not available",
        )

    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    # Run the task in background
    async def run_task():
        await scheduler._run_task_async(task_id)

    background_tasks.add_task(run_task)

    return {
        "status": "started",
        "task_id": task_id,
        "task_name": task.name,
        "message": f"Task '{task.name}' is running in background",
    }


@router.delete("/scheduler/tasks/{task_id}", dependencies=[Depends(require_admin_auth)])
async def delete_scheduler_task_admin(task_id: str):
    """
    Delete a single scheduled task by ID.
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not available",
        )

    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    # Remove the single task
    removed = scheduler.remove_task(task_id)

    if removed:
        return {
            "status": "deleted",
            "task_id": task_id,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {task_id}",
        )


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
    grouped: Dict[str, Any] = {}

    for pid in persona_ids:
        # Use the correct method: list_discovery_history
        discoveries = kb.list_discovery_history(pid, limit=limit)
        persona = kb.load_persona(pid)
        persona_name = persona.identity.name if persona else pid

        if pid not in grouped:
            grouped[pid] = {
                "persona_name": persona_name,
                "topics": [],
            }

        for d in discoveries[:limit]:
            # Extract data from the raw JSON structure
            report = d.get("report", {})

            # Get discovery ID from report or filename
            discovery_id = report.get("id", d.get("_filename", ""))

            # Get platform
            platform = d.get("platform", "unknown")

            # Extract trending topics from pattern_analysis (it's a list of strings)
            topics_list = []
            pattern_analysis = d.get("pattern_analysis", {})
            if pattern_analysis:
                trending = pattern_analysis.get("trending_topics", [])
                # trending_topics is already a list of strings
                topics_list = trending[:5] if trending else []

            # Extract content ideas
            ideas_list = []
            raw_ideas = d.get("ideas", [])
            if raw_ideas:
                ideas_list = [idea.get("topic", "") for idea in raw_ideas[:3] if idea.get("topic")]

            # Get timestamp
            discovered_at = d.get("created_at")

            topic_data = {
                "id": discovery_id,
                "platform": platform,
                "topics": topics_list,
                "ideas": ideas_list,
                "discovered_at": discovered_at,
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
    """Get detailed connector status and capabilities for admin."""
    import os
    from avatarfactory.connectors.registry import ConnectorRegistry

    all_capabilities = ConnectorRegistry.get_all_capabilities()

    connectors = []
    for platform, caps in all_capabilities.items():
        env_keys = [f.env_var for f in caps.config_fields if f.env_var]
        configured_keys = [(k, os.getenv(k) is not None) for k in env_keys]
        all_configured = all(v for _, v in configured_keys) if configured_keys else False

        connectors.append({
            "platform": caps.platform,
            "display_name": caps.display_name,
            "description": caps.description,
            "registered": True,
            "configured": all_configured,
            "env_keys": [{
                "key": k,
                "configured": v,
            } for k, v in configured_keys],
            "supports_topic_discovery": caps.supports_topic_discovery,
            "supports_persona_discovery": caps.supports_persona_discovery,
            "supports_publishing": caps.supports_publishing,
            "supports_fetching": caps.supports_fetching,
            "config_fields": [f.model_dump() for f in caps.config_fields],
            "integration_type": caps.integration_type.value,
            "usage_guide": caps.usage_guide,
        })

    return {
        "connectors": connectors,
        "configured_count": sum(1 for c in connectors if c["configured"]),
        "total_count": len(connectors),
        "topic_discovery_connectors": ConnectorRegistry.list_topic_discovery_connectors(),
        "persona_discovery_connectors": ConnectorRegistry.list_persona_discovery_connectors(),
    }


# =============================================================================
# Recommendations Endpoints
# =============================================================================


@router.get("/recommendations/personas", dependencies=[Depends(require_admin_auth)])
async def list_recommended_personas(
    limit: int = 20,
    domain: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    List recommended personas discovered by system tasks.

    Args:
        limit: Maximum number of recommendations to return
        domain: Filter by domain (e.g., "tech", "lifestyle")
        status: Filter by status (active, adopted, archived)
    """
    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    try:
        recommendations = kb.get_recommended_personas(
            limit=limit,
            domain=domain,
            status=status,
        )

        return {
            "count": len(recommendations),
            "recommendations": [
                {
                    "id": rec.id,
                    "name": rec.name,
                    "tagline": rec.tagline,
                    "domain": rec.domain,
                    "expertise": rec.expertise,
                    "content_pillars": rec.content_pillars,
                    "target_audience": rec.target_audience,
                    "relevance_score": rec.relevance_score,
                    "potential_score": rec.potential_score,
                    "rationale": rec.rationale,
                    "source_platforms": rec.source_platforms,
                    "source_trends": rec.source_trends[:3] if rec.source_trends else [],
                    "status": rec.status.value if hasattr(rec.status, 'value') else rec.status,
                    "created_at": rec.created_at.isoformat() if rec.created_at else None,
                }
                for rec in recommendations
            ],
        }
    except Exception as e:
        return {"count": 0, "recommendations": [], "error": str(e)}


@router.get("/recommendations/system-tasks", dependencies=[Depends(require_admin_auth)])
async def get_system_tasks_status():
    """
    Get status of system tasks (trend scan and persona recommendation).

    Returns task info, last run time, and next scheduled run.
    """
    scheduler = get_scheduler()

    if not scheduler:
        return {"tasks": [], "scheduler_running": False}

    tasks = scheduler.list_tasks()
    system_tasks = [t for t in tasks if t.persona_id is None]

    # Get next run times
    next_runs = scheduler.get_next_runs() if scheduler.is_running() else []
    next_run_map = {nr["task_id"]: nr["next_run"] for nr in next_runs}

    result = []
    for t in system_tasks:
        result.append({
            "id": t.id,
            "task_type": t.task_type,
            "schedule": t.schedule,
            "enabled": t.enabled,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "run_count": t.run_count,
            "next_run": next_run_map.get(t.id),
        })

    return {
        "tasks": result,
        "scheduler_running": scheduler.is_running(),
    }


# =============================================================================
# Trends Endpoints (for Connectors page)
# =============================================================================


@router.get("/trends/{platform}", dependencies=[Depends(require_admin_auth)])
async def get_trends_by_platform(platform: str, limit: int = 10):
    """
    Get latest trend snapshots for a specific platform.

    Returns trending topics, hashtags, and themes discovered by Trend Scan tasks.
    """
    orchestrator = get_orchestrator()
    kb = orchestrator.kb

    try:
        snapshots = kb.get_latest_trend_snapshots(platform=platform, limit=limit)

        return {
            "platform": platform,
            "count": len(snapshots),
            "snapshots": [
                {
                    "id": s.id,
                    "captured_at": s.captured_at.isoformat(),
                    "trending_topics": s.trending_topics[:10],
                    "trending_hashtags": s.trending_hashtags[:10],
                    "key_themes": s.key_themes[:5],
                    "analysis_summary": s.analysis_summary[:500] if s.analysis_summary else "",
                }
                for s in snapshots
            ],
        }
    except Exception as e:
        return {"platform": platform, "count": 0, "snapshots": [], "error": str(e)}


class CreateTrendScanTaskRequest(BaseModel):
    """Request to create a trend scan task for a platform."""
    schedule: str = Field(default="0 8 * * *", description="Cron schedule expression")
    limit: int = Field(default=30, description="Number of posts to fetch per scan")
    enabled: bool = Field(default=True, description="Whether task is enabled")


@router.get("/connectors/{platform}/task", dependencies=[Depends(require_admin_auth)])
async def get_connector_trend_task(platform: str):
    """
    Get the Trend Scan task configuration for a specific platform.

    Returns the task details if it exists, null otherwise.
    """
    scheduler = get_scheduler()

    if not scheduler:
        return {"task": None, "scheduler_available": False}

    # Look for trend_scan task for this platform
    task_id = f"trend_scan_{platform}"
    task = scheduler.get_task(task_id)

    if not task:
        # Also check for system tasks that might target this platform
        all_tasks = scheduler.list_tasks()
        for t in all_tasks:
            if t.task_type == "trend_scan" and t.platform == platform:
                task = t
                break

    if not task:
        return {"task": None, "scheduler_available": True}

    # Get next run time
    next_runs = scheduler.get_next_runs() if scheduler.is_running() else []
    next_run_map = {nr["task_id"]: nr["next_run"] for nr in next_runs}

    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "task_type": task.task_type,
            "platform": task.platform,
            "schedule": task.schedule,
            "enabled": task.enabled,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_status": task.last_status,
            "run_count": task.run_count,
            "next_run": next_run_map.get(task.id),
        },
        "scheduler_available": True,
    }


@router.post("/connectors/{platform}/task", dependencies=[Depends(require_admin_auth)])
async def create_connector_trend_task(platform: str, request: CreateTrendScanTaskRequest):
    """
    Create or update a Trend Scan task for a specific platform.

    Task ID format: trend_scan_{platform}
    """
    scheduler = get_scheduler()

    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not available",
        )

    # Verify platform is valid
    from avatarfactory.connectors.registry import ConnectorRegistry

    all_capabilities = ConnectorRegistry.get_all_capabilities()
    if platform not in all_capabilities:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform} not found",
        )

    caps = all_capabilities[platform]
    if not caps.supports_topic_discovery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform {platform} does not support topic discovery",
        )

    # Task ID and name
    task_id = f"trend_scan_{platform}"
    task_name = f"Trend Scan - {caps.display_name}"

    # Check if task exists
    existing_task = scheduler.get_task(task_id)

    if existing_task:
        # Update existing task
        scheduler.remove_task(task_id)

    # Create task
    task = scheduler.add_task_from_dict({
        "id": task_id,
        "name": task_name,
        "task_type": "trend_scan",
        "schedule": request.schedule,
        "platform": platform,
        "persona_id": None,  # System task
        "enabled": request.enabled,
        "config": {
            "limit": request.limit,
        },
    })

    return {
        "status": "created" if not existing_task else "updated",
        "task_id": task.id,
        "task_name": task.name,
        "schedule": task.schedule,
        "platform": platform,
    }
