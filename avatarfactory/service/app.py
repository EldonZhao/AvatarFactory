"""
FastAPI application for AvatarFactory.

Provides REST API endpoints for persona management, content generation,
and scheduler control.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# FastAPI imports with graceful fallback
try:
    from fastapi import BackgroundTasks, FastAPI, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
except ImportError:
    raise ImportError(
        "FastAPI is required for the service layer. "
        "Install with: pip install avatarfactory[service]"
    )


# =============================================================================
# Request/Response Models
# =============================================================================


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    persona_id: Optional[str] = Field(None, description="Active persona ID")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    metadata: Dict[str, Any] = {}


# -----------------------------------------------------------------------------
# Persona Models
# -----------------------------------------------------------------------------


class IdentityRequest(BaseModel):
    """Persona identity configuration."""
    name: str = Field(..., description="Persona name/title")
    tagline: str = Field(..., description="One-line positioning statement")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")


class TargetAudienceRequest(BaseModel):
    """Target audience definition."""
    primary: str = Field(..., description="Primary audience description")
    pain_points: List[str] = Field(default_factory=list, description="Audience pain points")
    goals: List[str] = Field(default_factory=list, description="Audience goals")


class VoiceStyleRequest(BaseModel):
    """Voice and tone configuration."""
    tone: str = Field(..., description="Overall tone (e.g., professional, casual)")
    language_patterns: List[str] = Field(default_factory=list, description="Language patterns")
    emoji_usage: str = Field(default="moderate", description="Emoji usage: none, minimal, moderate, heavy")


class ContentPillarRequest(BaseModel):
    """Content pillar definition."""
    name: str = Field(..., description="Pillar name")
    description: str = Field(default="", description="Pillar description")
    frequency: str = Field(default="weekly", description="Posting frequency")
    examples: List[str] = Field(default_factory=list, description="Example topics")


class BoundariesRequest(BaseModel):
    """Content boundaries and compliance rules."""
    avoid: List[str] = Field(default_factory=list, description="Topics/patterns to avoid")
    compliance: List[str] = Field(default_factory=list, description="Compliance requirements")


class NotificationConfigRequest(BaseModel):
    """Notification configuration."""
    enabled: bool = Field(default=False, description="Enable notifications")
    connector_type: str = Field(default="wecom", description="Connector type: wecom, slack, discord")
    # Note: webhook_url is configured at system level via AVATARFACTORY_WEBHOOK_URL env var
    notify_on_content: bool = Field(default=True, description="Notify on content generation")
    notify_on_review: bool = Field(default=True, description="Notify on review completion")
    notify_on_discovery: bool = Field(default=True, description="Notify on discovery completion")


class PersonaRequest(BaseModel):
    """Persona creation request - full schema."""
    # Simple mode: just description, LLM generates the rest
    description: Optional[str] = Field(None, description="Natural language persona description (simple mode)")

    # Structured mode: provide full details
    identity: Optional[IdentityRequest] = Field(None, description="Persona identity")
    target_audience: Optional[TargetAudienceRequest] = Field(None, description="Target audience")
    voice_style: Optional[VoiceStyleRequest] = Field(None, description="Voice and tone style")
    content_pillars: Optional[List[ContentPillarRequest]] = Field(None, description="Content pillars")
    boundaries: Optional[BoundariesRequest] = Field(None, description="Content boundaries")

    # Common fields
    platforms: List[str] = Field(default=["xiaohongshu"], description="Target platforms")
    notification: Optional[NotificationConfigRequest] = Field(None, description="Notification settings")


class PersonaResponse(BaseModel):
    """Persona response model - full details."""
    id: str
    version: str
    name: str
    tagline: str
    expertise: List[str] = []
    target_audience: Optional[Dict[str, Any]] = None
    voice_style: Optional[Dict[str, Any]] = None
    content_pillars: Optional[List[Dict[str, Any]]] = None
    boundaries: Optional[Dict[str, Any]] = None
    platforms: List[str] = []
    notification: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ContentRequest(BaseModel):
    """Content generation request."""
    persona_id: str = Field(..., description="Persona ID")
    topic: str = Field(..., description="Content topic")
    pillar: Optional[str] = Field(None, description="Content pillar")
    template: str = Field("comparison", description="Content template")
    use_trending: bool = Field(True, description="Use trending data")
    variant_count: int = Field(1, description="Number of variants", ge=1, le=5)


class ContentResponse(BaseModel):
    """Content response model."""
    id: str
    title: str
    body: str
    tags: List[str]
    platform: str
    review_score: Optional[int] = None


class SchedulerStatusResponse(BaseModel):
    """Scheduler status response."""
    running: bool
    task_count: int
    next_run: Optional[str] = None


class SetupTasksRequest(BaseModel):
    """Request to set up proactive tasks."""
    platforms: List[str] = Field(default=["bluesky"], description="Platforms to monitor (deprecated, use discovery_platforms)")
    discovery_platforms: Optional[List[str]] = Field(default=None, description="Platforms for discovery/trending scan")
    content_platforms: Optional[List[str]] = Field(default=None, description="Platforms for content generation")
    discovery_schedule: Optional[str] = Field(default=None, description="Cron schedule for discovery (default: 0 */6 * * *)")
    content_schedule: Optional[str] = Field(default=None, description="Cron schedule for content generation (default: 0 9 * * *)")


class SetupTasksResponse(BaseModel):
    """Response from setting up tasks."""
    tasks_created: int
    task_ids: List[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


# =============================================================================
# Global State
# =============================================================================

_orchestrator = None
_scheduler = None


def get_orchestrator():
    """Get the orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized",
        )
    return _orchestrator


def get_scheduler():
    """Get the scheduler instance."""
    global _scheduler
    return _scheduler


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Initializes orchestrator and scheduler on startup,
    cleans up on shutdown.
    """
    global _orchestrator, _scheduler

    from avatarfactory.agents.proactive_orchestrator import ProactiveOrchestrator
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory
    from avatarfactory.scheduler.engine import Scheduler, SchedulerConfig

    # Initialize knowledges
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)

    # Initialize LLM provider
    llm_provider = LLMProviderFactory.from_env()

    # Initialize scheduler
    scheduler_config = SchedulerConfig()
    _scheduler = Scheduler(scheduler_config)

    # Initialize orchestrator with scheduler
    _orchestrator = ProactiveOrchestrator(
        knowledge_base=kb,
        llm_provider=llm_provider,
        scheduler=_scheduler,
    )

    # Start scheduler in non-blocking mode
    _scheduler.start(blocking=False)

    yield

    # Shutdown
    if _scheduler:
        _scheduler.stop()


# =============================================================================
# Application Factory
# =============================================================================


def create_app(
    title: str = "AvatarFactory API",
    version: str = "1.0.0",
    enable_cors: bool = True,
) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        title: API title
        version: API version
        enable_cors: Whether to enable CORS middleware

    Returns:
        Configured FastAPI application
    """
    application = FastAPI(
        title=title,
        version=version,
        description="AI-powered persona management and content generation API",
        lifespan=lifespan,
    )

    if enable_cors:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register routes
    register_routes(application)

    return application


def register_routes(app: FastAPI):
    """Register API routes."""

    # -------------------------------------------------------------------------
    # Health & Info
    # -------------------------------------------------------------------------

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(status="healthy", version="1.0.0")

    @app.get("/", tags=["System"])
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "AvatarFactory API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    # -------------------------------------------------------------------------
    # Chat
    # -------------------------------------------------------------------------

    @app.post("/chat", response_model=ChatResponse, tags=["Chat"])
    async def chat(request: ChatRequest):
        """
        Process a chat message.

        Handles natural language commands and routes them to appropriate agents.
        """
        orchestrator = get_orchestrator()

        from avatarfactory.models.schemas import AgentMessage, TaskType

        message = AgentMessage(
            sender="user",
            receiver="orchestrator",
            task_type=TaskType.CHAT,
            payload={
                "user_input": request.message,
                "persona_id": request.persona_id,
            },
            context={},
        )

        try:
            result = await orchestrator.process(message)
            return ChatResponse(
                response=result.get("message", str(result)),
                metadata=result,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    # -------------------------------------------------------------------------
    # Personas
    # -------------------------------------------------------------------------

    @app.get("/personas", tags=["Personas"])
    async def list_personas():
        """List all personas."""
        orchestrator = get_orchestrator()
        persona_ids = orchestrator.kb.list_personas()
        personas = []
        for pid in persona_ids:
            p = orchestrator.kb.load_persona(pid)
            if p:
                personas.append({
                    "id": p.id,
                    "name": p.identity.name,
                    "tagline": p.identity.tagline,
                    "version": p.version,
                    "platforms": [pt.value for pt in p.platforms],
                })
        return {
            "count": len(personas),
            "personas": personas,
        }

    @app.get("/personas/{persona_id}", tags=["Personas"])
    async def get_persona(persona_id: str):
        """Get a specific persona."""
        orchestrator = get_orchestrator()
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )
        return persona.model_dump()

    @app.post("/personas", response_model=PersonaResponse, tags=["Personas"])
    async def create_persona(request: PersonaRequest):
        """Create a new persona.

        Supports two modes:
        - Simple mode: provide only `description` for AI-generated persona
        - Structured mode: provide detailed fields (identity, target_audience, etc.)
        """
        orchestrator = get_orchestrator()

        from avatarfactory.models.schemas import AgentMessage, TaskType

        # Build payload based on mode
        payload: Dict[str, Any] = {}

        if request.identity is not None:
            # Structured mode: use provided fields directly
            payload["structured"] = True
            payload["identity"] = request.identity.model_dump() if request.identity else None
            payload["target_audience"] = (
                request.target_audience.model_dump() if request.target_audience else None
            )
            payload["voice_style"] = (
                request.voice_style.model_dump() if request.voice_style else None
            )
            payload["content_pillars"] = (
                [p.model_dump() for p in request.content_pillars]
                if request.content_pillars
                else None
            )
            payload["boundaries"] = (
                request.boundaries.model_dump() if request.boundaries else None
            )
            payload["platforms"] = request.platforms
            payload["notification"] = (
                request.notification.model_dump() if request.notification else None
            )
        else:
            # Simple mode: AI generates from description
            payload["structured"] = False
            payload["user_input"] = f"Create a persona: {request.description}"
            payload["platforms"] = request.platforms

        message = AgentMessage(
            sender="api",
            receiver="orchestrator",
            task_type=TaskType.CREATE_PERSONA,
            payload=payload,
            context={},
        )

        try:
            result = await orchestrator.process(message)
            persona_data = result.get("persona", {})

            # Build response with all available fields
            identity = persona_data.get("identity", {})
            return PersonaResponse(
                id=persona_data.get("id", ""),
                version=persona_data.get("version", "v1.0"),
                name=identity.get("name", ""),
                tagline=identity.get("tagline", ""),
                expertise=identity.get("expertise", []),
                target_audience=persona_data.get("target_audience"),
                voice_style=persona_data.get("voice_style"),
                content_pillars=persona_data.get("content_pillars"),
                boundaries=persona_data.get("boundaries"),
                platforms=persona_data.get("platforms", []),
                notification=persona_data.get("notification"),
                created_at=persona_data.get("created_at"),
                updated_at=persona_data.get("updated_at"),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    @app.delete("/personas/{persona_id}", tags=["Personas"])
    async def delete_persona(persona_id: str, keep_content: bool = False):
        """Delete a persona and all associated data.

        This will remove:
        - Persona configuration and versions
        - All content created by this persona (unless keep_content=True)
        - Discovery data
        - Scheduled tasks for this persona
        """
        orchestrator = get_orchestrator()

        # Check if persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Delete scheduled tasks
        from avatarfactory.scheduler.engine import Scheduler, SchedulerConfig
        scheduler = Scheduler(SchedulerConfig())
        tasks_removed = scheduler.remove_tasks_for_persona(persona_id)

        # Delete persona and content
        result = orchestrator.kb.delete_persona(persona_id, delete_content=not keep_content)

        return {
            "status": "success",
            "persona_id": persona_id,
            "persona_deleted": result["persona_deleted"],
            "content_deleted": result["content_deleted"],
            "discovery_deleted": result["discovery_deleted"],
            "tasks_removed": tasks_removed,
            "errors": result["errors"],
        }

    # -------------------------------------------------------------------------
    # Content
    # -------------------------------------------------------------------------

    @app.post("/content/generate", response_model=ContentResponse, tags=["Content"])
    async def generate_content(request: ContentRequest):
        """Generate content for a persona."""
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(request.persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {request.persona_id} not found",
            )

        # Determine pillar
        pillar = request.pillar
        if not pillar and persona.content_pillars:
            pillar = persona.content_pillars[0].name

        from avatarfactory.models.schemas import AgentMessage, TaskType

        message = AgentMessage(
            sender="api",
            receiver="content",
            task_type=TaskType.GENERATE_CONTENT,
            payload={
                "persona_id": request.persona_id,
                "pillar": pillar,
                "topic": request.topic,
                "template": request.template,
                "use_trending": request.use_trending,
                "variant_count": request.variant_count,
            },
            context={},
        )

        try:
            content = await orchestrator.content_agent.process(message)
            return ContentResponse(
                id=content.id,
                title=content.title,
                body=content.body,
                tags=content.tags,
                platform=content.platform.value,
                review_score=content.review_score,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    @app.get("/content", tags=["Content"])
    async def list_content(
        persona_id: Optional[str] = None,
        status: Optional[str] = "draft",
        limit: int = 20,
    ):
        """List content items."""
        orchestrator = get_orchestrator()
        contents = orchestrator.kb.list_content(
            persona_id=persona_id,
            status=status,
        )[:limit]
        return {
            "count": len(contents),
            "content": [
                {
                    "id": c.id,
                    "title": c.title,
                    "persona_id": c.persona_id,
                    "platform": c.platform.value,
                    "pillar": c.pillar,
                    "review_score": c.review_score,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in contents
            ],
        }

    @app.get("/content/{content_id}", tags=["Content"])
    async def get_content(content_id: str):
        """Get a specific content item by ID."""
        orchestrator = get_orchestrator()

        # Try loading from draft first, then published
        content = orchestrator.kb.load_content(content_id, status="draft")
        content_status = "draft"
        if not content:
            content = orchestrator.kb.load_content(content_id, status="published")
            content_status = "published"

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content {content_id} not found",
            )

        return {
            "id": content.id,
            "title": content.title,
            "body": content.body,
            "tags": content.tags,
            "persona_id": content.persona_id,
            "platform": content.platform.value,
            "pillar": content.pillar,
            "review_score": content.review_score,
            "review_issues": content.review_issues,
            "status": content_status,
            "created_at": content.created_at.isoformat() if content.created_at else None,
            "metadata": content.metadata,
            "media": [m.model_dump() for m in content.media] if content.media else [],
            "image_prompts": content.image_prompts,
            "predicted_engagement": content.predicted_engagement,
        }

    @app.get("/content/{content_id}/view", response_class=HTMLResponse, tags=["Content"])
    async def view_content_html(content_id: str):
        """View content as HTML page (for WeChat Work news card link)."""
        import html as html_lib

        orchestrator = get_orchestrator()

        # Try loading from draft first, then published
        content = orchestrator.kb.load_content(content_id, status="draft")
        content_status = "draft"
        if not content:
            content = orchestrator.kb.load_content(content_id, status="published")
            content_status = "published"

        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content {content_id} not found",
            )

        # Load persona for display
        persona = orchestrator.kb.load_persona(content.persona_id)
        persona_name = persona.identity.name if persona else content.persona_id

        # Normalize content for better Markdown rendering
        body_content = content.body
        # Convert Chinese horizontal lines to Markdown horizontal rule
        body_content = body_content.replace('———', '\n\n---\n\n')
        body_content = body_content.replace('——', '\n\n---\n\n')
        # Convert Chinese quotes to standard quotes for better display
        body_content = body_content.replace('「', '"').replace('」', '"')
        body_content = body_content.replace('『', '"').replace('』', '"')

        # Escape content body for safe embedding in JavaScript
        body_escaped = html_lib.escape(body_content).replace('`', '\\`').replace('$', '\\$')

        # Build tags HTML
        tags_html = ' '.join(f'<span class="tag">#{tag}</span>' for tag in content.tags[:10])

        # Review score badge
        score_html = ""
        if content.review_score is not None:
            if content.review_score >= 80:
                score_class = "score-high"
            elif content.review_score >= 60:
                score_class = "score-medium"
            else:
                score_class = "score-low"
            score_html = f'<span class="score {score_class}">{content.review_score}/100</span>'

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_lib.escape(content.title)}</title>
    <!-- marked.js for Markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.8;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 28px;
            color: #1a1a1a;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        .meta {{
            font-size: 16px;
            color: #666;
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: center;
        }}
        .meta span {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .score {{
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 500;
        }}
        .score-high {{ background: #e6f7e6; color: #2e7d32; }}
        .score-medium {{ background: #fff3e0; color: #ef6c00; }}
        .score-low {{ background: #ffebee; color: #c62828; }}
        .content {{
            font-size: 18px;
            color: #333;
        }}
        .content h1 {{ font-size: 28px; margin: 24px 0 16px; color: #1a1a1a; font-weight: 600; }}
        .content h2 {{ font-size: 24px; margin: 20px 0 12px; color: #1a1a1a; font-weight: 600; }}
        .content h3 {{ font-size: 20px; margin: 16px 0 10px; color: #333; font-weight: 600; }}
        .content h4 {{ font-size: 18px; margin: 14px 0 8px; color: #333; font-weight: 600; }}
        .content p {{ margin-bottom: 16px; }}
        .content ul, .content ol {{
            margin: 16px 0;
            padding-left: 28px;
        }}
        .content li {{
            margin-bottom: 8px;
        }}
        .content code {{
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 16px;
            color: #e83e8c;
        }}
        .content pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0;
        }}
        .content pre code {{
            background: none;
            padding: 0;
            color: inherit;
        }}
        .content blockquote {{
            border-left: 4px solid #1976d2;
            padding-left: 16px;
            margin: 16px 0;
            color: #555;
            background: #f9f9f9;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
        }}
        .content a {{
            color: #1976d2;
            text-decoration: none;
        }}
        .content a:hover {{
            text-decoration: underline;
        }}
        .content strong {{
            font-weight: 600;
        }}
        .content em {{
            font-style: italic;
        }}
        .content hr {{
            border: none;
            border-top: 1px solid #eee;
            margin: 24px 0;
        }}
        .content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        .content th, .content td {{
            border: 1px solid #ddd;
            padding: 10px 12px;
            text-align: left;
        }}
        .content th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        .content img {{
            max-width: 100%;
            border-radius: 8px;
            margin: 16px 0;
        }}
        .tags {{
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid #eee;
        }}
        .tag {{
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 6px 14px;
            border-radius: 16px;
            font-size: 15px;
            margin-right: 8px;
            margin-bottom: 8px;
        }}
        .footer {{
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid #eee;
            font-size: 14px;
            color: #999;
            text-align: center;
        }}
        .status-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            background: #e3f2fd;
            color: #1976d2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">{html_lib.escape(content.title)}</h1>
            <div class="meta">
                <span>👤 {html_lib.escape(persona_name)}</span>
                {score_html}
            </div>
        </div>
        <div class="content" id="content"></div>
        <div class="tags">
            {tags_html}
        </div>
        <div class="footer">
            <p>由 AvatarFactory 生成 | {content.created_at.strftime('%Y-%m-%d %H:%M') if content.created_at else ''}</p>
        </div>
    </div>
    <script>
        // Markdown content
        const markdownContent = `{body_escaped}`;

        // Configure marked options
        marked.setOptions({{
            breaks: true,
            gfm: true
        }});

        // Render markdown to HTML
        document.getElementById('content').innerHTML = marked.parse(markdownContent);
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html)

    # -------------------------------------------------------------------------
    # Scheduler
    # -------------------------------------------------------------------------

    @app.get("/scheduler/status", response_model=SchedulerStatusResponse, tags=["Scheduler"])
    async def scheduler_status():
        """Get scheduler status."""
        scheduler = get_scheduler()
        if not scheduler:
            return SchedulerStatusResponse(running=False, task_count=0)

        next_runs = scheduler.get_next_runs()
        next_run = next_runs[0].get("next_run") if next_runs else None

        return SchedulerStatusResponse(
            running=scheduler.is_running(),
            task_count=len(scheduler.list_tasks()),
            next_run=next_run,
        )

    @app.get("/scheduler/tasks", tags=["Scheduler"])
    async def list_scheduler_tasks():
        """List all scheduled tasks."""
        scheduler = get_scheduler()
        if not scheduler:
            return {"tasks": []}

        tasks = scheduler.list_tasks()
        return {
            "count": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "task_type": t.task_type,
                    "schedule": t.schedule,
                    "persona_id": t.persona_id,
                    "platform": t.platform,
                    "enabled": t.enabled,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "last_status": t.last_status,
                    "last_error": t.last_error,
                    "run_count": t.run_count,
                }
                for t in tasks
            ],
        }

    @app.post(
        "/scheduler/tasks/{persona_id}/setup",
        response_model=SetupTasksResponse,
        tags=["Scheduler"],
    )
    async def setup_persona_tasks(persona_id: str, request: SetupTasksRequest):
        """Set up proactive tasks for a persona."""
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Use new separate platforms or fall back to legacy 'platforms' field
        discovery_platforms = request.discovery_platforms or request.platforms
        content_platforms = request.content_platforms or request.platforms

        tasks = await orchestrator.setup_persona_tasks(
            persona_id,
            discovery_platforms=discovery_platforms,
            content_platforms=content_platforms,
            discovery_schedule=request.discovery_schedule,
            content_schedule=request.content_schedule,
        )
        return SetupTasksResponse(
            tasks_created=len(tasks),
            task_ids=[t["id"] for t in tasks],
        )

    @app.delete("/scheduler/tasks/{persona_id}", tags=["Scheduler"])
    async def remove_persona_tasks(persona_id: str):
        """Remove all proactive tasks for a persona."""
        orchestrator = get_orchestrator()
        removed = await orchestrator.remove_persona_tasks(persona_id)
        return {"removed": removed}

    @app.post("/scheduler/tasks/{task_id}/run", tags=["Scheduler"])
    async def run_scheduler_task(task_id: str, background_tasks: BackgroundTasks):
        """
        Run a scheduled task immediately.

        The task runs in the background and results are sent via webhook notification.
        """
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")

        task = scheduler.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        # Run the task in background
        async def run_task():
            from avatarfactory.scheduler.tasks import TaskRegistry
            import logging

            logger = logging.getLogger("avatarfactory.scheduler")
            logger.info(f"Running task manually: {task.name}")

            try:
                runner = TaskRegistry.get_runner(task.task_type)
                if runner:
                    result = await runner(task)
                    task.last_run = datetime.now()
                    task.run_count += 1
                    task.last_status = "success" if result.get("success") else "error"
                    task.last_error = result.get("error") if not result.get("success") else None

                    # Send notification
                    await scheduler._notify_task_completed(task, result)
                    scheduler._save_state()
                else:
                    task.last_status = "error"
                    task.last_error = f"Unknown task type: {task.task_type}"
                    scheduler._save_state()
            except Exception as e:
                logger.error(f"Task {task.name} failed: {e}")
                task.last_status = "error"
                task.last_error = str(e)
                await scheduler._notify_task_failed(task, str(e))
                scheduler._save_state()

        background_tasks.add_task(run_task)

        return {
            "status": "started",
            "task_id": task_id,
            "task_name": task.name,
            "message": f"Task '{task.name}' is running in background",
        }

    # -------------------------------------------------------------------------
    # Topology & System Info
    # -------------------------------------------------------------------------

    @app.get("/topology", tags=["System"])
    async def get_topology():
        """
        Get system topology data for visualization.

        Returns nodes and edges representing:
        - Personas and their content
        - Agents in the system
        - Platform connectors
        - Scheduled tasks
        """
        orchestrator = get_orchestrator()
        kb = orchestrator.kb

        nodes = []
        edges = []

        # Color scheme
        colors = {
            "persona": "#4A90D9",
            "agent": "#7B68EE",
            "connector": "#50C878",
            "task": "#FFB347",
        }

        # Add agent nodes
        agents = [
            ("orchestrator", "Orchestrator"),
            ("persona_agent", "Persona Agent"),
            ("content_agent", "Content Agent"),
            ("discovery_agent", "Discovery Agent"),
            ("review_agent", "Review Agent"),
        ]
        for agent_id, agent_name in agents:
            nodes.append({
                "id": agent_id,
                "label": agent_name,
                "type": "agent",
                "size": 30,
                "color": colors["agent"],
            })

        # Orchestrator connects to all agents
        for agent_id, _ in agents[1:]:
            edges.append({
                "source": "orchestrator",
                "target": agent_id,
                "label": "manages",
            })

        # Add persona nodes
        for persona_id in kb.list_personas():
            persona = kb.load_persona(persona_id)
            if persona:
                draft_count = len(kb.list_content(persona_id, status="draft"))
                published_count = len(kb.list_content(persona_id, status="published"))

                nodes.append({
                    "id": f"persona_{persona_id}",
                    "label": persona.identity.name,
                    "type": "persona",
                    "size": 35,
                    "color": colors["persona"],
                    "metadata": {
                        "draft": draft_count,
                        "published": published_count,
                    },
                })
                edges.append({
                    "source": "persona_agent",
                    "target": f"persona_{persona_id}",
                    "label": "manages",
                })

        # Add connector nodes
        from avatarfactory.connectors.registry import ConnectorRegistry

        connector_configs = {
            "bluesky": ["BLUESKY_USERNAME", "BLUESKY_PASSWORD"],
            "twitter": ["TWITTER_API_KEY"],
            "xiaohongshu": ["XIAOHONGSHU_COOKIE"],
            "wecom": ["AVATARFACTORY_WEBHOOK_URL"],
        }

        for platform, env_keys in connector_configs.items():
            configured = all(os.getenv(k) for k in env_keys)
            node_color = colors["connector"] if configured else "#CCCCCC"

            nodes.append({
                "id": f"connector_{platform}",
                "label": platform.capitalize(),
                "type": "connector",
                "size": 25,
                "color": node_color,
                "configured": configured,
            })
            edges.append({
                "source": "discovery_agent",
                "target": f"connector_{platform}",
                "label": "fetches from",
            })

        # Add task nodes
        scheduler = get_scheduler()
        if scheduler:
            for task in scheduler.list_tasks()[:10]:
                task_color = colors["task"] if task.enabled else "#CCCCCC"
                nodes.append({
                    "id": f"task_{task.id}",
                    "label": task.name[:20],
                    "type": "task",
                    "size": 20,
                    "color": task_color,
                    "enabled": task.enabled,
                })
                if task.persona_id:
                    edges.append({
                        "source": f"task_{task.id}",
                        "target": f"persona_{task.persona_id}",
                        "label": "targets",
                    })

        return {
            "nodes": nodes,
            "edges": edges,
        }

    @app.get("/connectors/status", tags=["System"])
    async def get_connectors_status():
        """
        Get configuration status of all platform connectors.

        Returns whether each connector is registered and configured.
        """
        from avatarfactory.connectors.registry import ConnectorRegistry

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
        }

        statuses = []
        for platform, config in connector_configs.items():
            registered = ConnectorRegistry.is_registered(platform)
            configured = all(os.getenv(k) is not None for k in config["env_keys"])
            missing_keys = [k for k in config["env_keys"] if not os.getenv(k)]

            statuses.append({
                "platform": platform,
                "description": config["description"],
                "registered": registered,
                "configured": configured,
                "missing_keys": missing_keys,
            })

        return {
            "connectors": statuses,
            "configured_count": sum(1 for s in statuses if s["configured"]),
            "total_count": len(statuses),
        }

    # -------------------------------------------------------------------------
    # Evolution
    # -------------------------------------------------------------------------

    @app.get("/personas/{persona_id}/evolution/suggestions", tags=["Evolution"])
    async def list_evolution_suggestions(
        persona_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        """List evolution suggestions for a persona."""
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        suggestions = orchestrator.kb.list_evolution_suggestions(
            persona_id, status=status, limit=limit
        )

        return {
            "count": len(suggestions),
            "suggestions": [s.model_dump(mode="json") for s in suggestions],
        }

    @app.post("/personas/{persona_id}/evolution/analyze", tags=["Evolution"])
    async def analyze_evolution(
        persona_id: str,
        period: str = "7d",
        background_tasks: BackgroundTasks = None,
    ):
        """
        Analyze feedback and generate evolution suggestions.

        This runs the evolution analysis which:
        1. Analyzes review scores and patterns
        2. Analyzes content performance
        3. Checks discovery alignment
        4. Generates improvement suggestions
        """
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Run analysis
        from avatarfactory.agents.evolution import EvolutionAgent
        evolution_agent = EvolutionAgent(
            knowledge_base=orchestrator.kb,
            llm_provider=orchestrator.llm_provider,
        )

        result = await evolution_agent.run_scheduled_evolution(persona_id)

        return {
            "status": "success",
            "persona_id": persona_id,
            "period": period,
            "suggestions_count": result.get("suggestions_count", 0),
            "auto_applied_count": result.get("auto_applied_count", 0),
            "pending_approval": result.get("pending_approval", []),
        }

    @app.post("/personas/{persona_id}/evolution/suggest", tags=["Evolution"])
    async def suggest_from_feedback(
        persona_id: str,
        feedback: str,
    ):
        """
        Generate evolution suggestions from user feedback.

        Provide natural language feedback like "make the tone more casual"
        and get specific suggestions for persona changes.
        """
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Generate suggestions
        from avatarfactory.agents.evolution import EvolutionAgent
        evolution_agent = EvolutionAgent(
            knowledge_base=orchestrator.kb,
            llm_provider=orchestrator.llm_provider,
        )

        suggestions = await evolution_agent.generate_suggestions_from_user_input(
            persona_id, feedback
        )

        return {
            "count": len(suggestions),
            "suggestions": [s.model_dump(mode="json") for s in suggestions],
        }

    class SuggestionReviewRequest(BaseModel):
        """Request to review a suggestion."""
        approved: bool = Field(..., description="Whether to approve the suggestion")
        rejection_reason: Optional[str] = Field(None, description="Reason for rejection")

    @app.post(
        "/personas/{persona_id}/evolution/suggestions/{suggestion_id}/review",
        tags=["Evolution"],
    )
    async def review_suggestion(
        persona_id: str,
        suggestion_id: str,
        request: SuggestionReviewRequest,
    ):
        """
        Approve or reject an evolution suggestion.

        Approved suggestions are automatically applied to the persona.
        """
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Review suggestion
        from avatarfactory.agents.evolution import EvolutionAgent
        evolution_agent = EvolutionAgent(
            knowledge_base=orchestrator.kb,
            llm_provider=orchestrator.llm_provider,
        )

        try:
            suggestion = await evolution_agent.review_suggestion(
                persona_id,
                suggestion_id,
                request.approved,
                request.rejection_reason,
            )
            return {
                "status": "approved" if request.approved else "rejected",
                "suggestion": suggestion.model_dump(mode="json"),
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    class RollbackRequest(BaseModel):
        """Request to rollback persona."""
        version: str = Field(..., description="Version to rollback to (e.g., 'v1.0')")

    @app.post("/personas/{persona_id}/evolution/rollback", tags=["Evolution"])
    async def rollback_persona(persona_id: str, request: RollbackRequest):
        """
        Rollback persona to a previous version.
        """
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Perform rollback
        from avatarfactory.agents.evolution import EvolutionAgent
        evolution_agent = EvolutionAgent(
            knowledge_base=orchestrator.kb,
            llm_provider=orchestrator.llm_provider,
        )

        try:
            restored = await evolution_agent.rollback_change(persona_id, request.version)
            return {
                "status": "success",
                "restored_from": request.version,
                "current_version": restored.version,
                "persona": restored.model_dump(mode="json"),
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    @app.get("/personas/{persona_id}/evolution/history", tags=["Evolution"])
    async def get_evolution_history(persona_id: str):
        """
        Get evolution history including version changes and applied suggestions.
        """
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        # Get version history
        versions = orchestrator.kb.get_persona_history(persona_id)

        # Get applied suggestions
        all_suggestions = orchestrator.kb.list_evolution_suggestions(persona_id)
        applied_suggestions = [
            s for s in all_suggestions
            if s.status.value in ("approved", "auto_applied")
        ]

        return {
            "persona_id": persona_id,
            "current_version": persona.version,
            "versions": [v.model_dump(mode="json") for v in versions],
            "available_versions": orchestrator.kb.list_persona_versions(persona_id),
            "applied_suggestions": [s.model_dump(mode="json") for s in applied_suggestions],
        }

    # -------------------------------------------------------------------------
    # Agent Configuration
    # -------------------------------------------------------------------------

    @app.get("/personas/{persona_id}/agents/{agent_type}/config", tags=["Evolution"])
    async def get_agent_config(persona_id: str, agent_type: str):
        """Get agent configuration for a persona."""
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        from avatarfactory.core.agent_config import AgentConfigManager
        config_manager = AgentConfigManager(orchestrator.kb)

        config = config_manager.get_config(persona_id, agent_type)
        return {
            "persona_id": persona_id,
            "agent_type": agent_type,
            "config": config.model_dump(),
        }

    class AgentConfigUpdateRequest(BaseModel):
        """Request to update agent configuration."""
        temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
        max_tokens: Optional[int] = Field(None, ge=100, le=8192)
        creativity_level: Optional[str] = Field(None)
        detail_level: Optional[str] = Field(None)
        system_prompt_additions: Optional[str] = Field(None)
        style_emphasis: Optional[List[str]] = Field(None)
        avoid_patterns: Optional[List[str]] = Field(None)

    @app.put("/personas/{persona_id}/agents/{agent_type}/config", tags=["Evolution"])
    async def update_agent_config(
        persona_id: str,
        agent_type: str,
        request: AgentConfigUpdateRequest,
    ):
        """Update agent configuration for a persona."""
        orchestrator = get_orchestrator()

        # Verify persona exists
        persona = orchestrator.kb.load_persona(persona_id)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona {persona_id} not found",
            )

        from avatarfactory.core.agent_config import AgentConfigManager
        config_manager = AgentConfigManager(orchestrator.kb)

        # Build updates from non-None fields
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided",
            )

        new_config = config_manager.update_config(persona_id, agent_type, updates)

        return {
            "status": "updated",
            "persona_id": persona_id,
            "agent_type": agent_type,
            "config": new_config.model_dump(),
        }


# =============================================================================
# Default Application Instance
# =============================================================================

app = create_app()
