"""
FastAPI application for AvatarFactory.

Provides REST API endpoints for persona management, content generation,
and scheduler control.
"""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# FastAPI imports with graceful fallback
try:
    from fastapi import FastAPI, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware
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


class PersonaRequest(BaseModel):
    """Persona creation request."""
    description: str = Field(..., description="Persona description")
    platform: str = Field("xiaohongshu", description="Target platform")


class PersonaResponse(BaseModel):
    """Persona response model."""
    id: str
    name: str
    tagline: str
    version: str


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
    platforms: List[str] = Field(default=["bluesky"], description="Platforms to monitor")


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

    # Initialize knowledge base
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
        """Create a new persona."""
        orchestrator = get_orchestrator()

        from avatarfactory.models.schemas import AgentMessage, TaskType

        message = AgentMessage(
            sender="api",
            receiver="orchestrator",
            task_type=TaskType.CREATE_PERSONA,
            payload={
                "user_input": f"Create a persona: {request.description}",
                "platform": request.platform,
            },
            context={},
        )

        try:
            result = await orchestrator.process(message)
            persona_data = result.get("persona", {})
            return PersonaResponse(
                id=persona_data.get("id", ""),
                name=persona_data.get("identity", {}).get("name", ""),
                tagline=persona_data.get("identity", {}).get("tagline", ""),
                version=persona_data.get("version", "v1.0"),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

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

        tasks = await orchestrator.setup_persona_tasks(persona_id, request.platforms)
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


# =============================================================================
# Default Application Instance
# =============================================================================

app = create_app()
