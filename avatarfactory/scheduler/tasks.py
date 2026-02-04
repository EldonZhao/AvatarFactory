"""
Task Runners for AvatarFactory Scheduler.

Contains implementations for different scheduled task types.
"""

import logging
import os
from typing import Any, Callable, Dict, Optional

from avatarfactory.scheduler.engine import PublishQueueItem, ScheduledTask

logger = logging.getLogger("avatarfactory.scheduler.tasks")


class TaskRegistry:
    """Registry of task runners."""

    _runners: Dict[str, Callable] = {}

    @classmethod
    def register(cls, task_type: str) -> Callable:
        """Decorator to register a task runner."""
        def decorator(func: Callable) -> Callable:
            cls._runners[task_type] = func
            return func
        return decorator

    @classmethod
    def get_runner(cls, task_type: str) -> Optional[Callable]:
        """Get runner for a task type."""
        return cls._runners.get(task_type)

    @classmethod
    def list_types(cls) -> list:
        """List available task types."""
        return list(cls._runners.keys())


# =============================================================================
# Task Runners
# =============================================================================


@TaskRegistry.register("discovery")
async def run_discovery_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run discovery task - fetch and analyze trending content.

    Expected task params:
    - persona_id: str
    - platform: str (default: bluesky)
    - query: str (optional)
    """
    from avatarfactory.agents.discovery import DiscoveryAgent
    from avatarfactory.core.knowledge_base import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory

    persona_id = task.persona_id
    platform = task.platform or "bluesky"
    query = task.extra_params.get("query")
    limit = task.extra_params.get("limit", 20)

    if not persona_id:
        return {"success": False, "error": "persona_id required for discovery"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    agent = DiscoveryAgent(knowledge_base=kb, llm_provider=provider)

    result = await agent.discover_and_analyze(
        persona_id=persona_id,
        platform=platform,
        query=query,
        limit=limit,
    )

    if result.get("status") == "success":
        data = result.get("data", {})
        return {
            "success": True,
            "trending_count": data.get("trending_count", 0),
            "ideas_count": len(data.get("ideas", [])),
            "suggestions": data.get("persona_suggestions", []),
        }
    else:
        return {"success": False, "error": result.get("message")}


@TaskRegistry.register("content")
async def run_content_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run content generation task.

    Expected task params:
    - persona_id: str
    - topic: str (optional - will use content pillars if not provided)
    - count: int (default: 1)
    """
    from avatarfactory.agents.orchestrator import OrchestratorAgent
    from avatarfactory.core.knowledge_base import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory
    from avatarfactory.models.schemas import AgentMessage

    persona_id = task.persona_id
    topic = task.extra_params.get("topic")
    count = task.extra_params.get("count", 1)

    if not persona_id:
        return {"success": False, "error": "persona_id required for content generation"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    orchestrator = OrchestratorAgent(knowledge_base=kb, llm_provider=provider)

    # If no topic, get one from persona's content pillars
    if not topic:
        persona = kb.load_persona(persona_id)
        if persona and persona.content_pillars:
            pillar = persona.content_pillars[0]
            if pillar.examples:
                topic = pillar.examples[0]
            else:
                topic = f"{pillar.name} tips"

    if not topic:
        return {"success": False, "error": "No topic available for content generation"}

    message = AgentMessage(
        sender="scheduler",
        receiver="orchestrator",
        task_type="chat",  # type: ignore
        payload={
            "user_input": f"Generate content about: {topic}",
            "persona_id": persona_id,
        },
        context={},
    )

    result = await orchestrator.process(message)

    if result.get("status") == "success":
        data = result.get("data", {})
        return {
            "success": True,
            "content_id": data.get("content", {}).get("id"),
            "title": data.get("content", {}).get("title"),
        }
    else:
        return {"success": False, "error": result.get("message")}


@TaskRegistry.register("publish")
async def run_publish_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run scheduled publish task - publishes pending queue items.

    This is handled by the scheduler's _process_publish_queue method.
    """
    return {"success": True, "message": "Publish handled by queue processor"}


@TaskRegistry.register("report")
async def run_report_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run weekly report generation task.

    Expected task params:
    - persona_id: str
    """
    from avatarfactory.core.knowledge_base import KnowledgeBase

    persona_id = task.persona_id
    if not persona_id:
        return {"success": False, "error": "persona_id required for report"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    # Get statistics
    stats = kb.get_storage_stats()
    contents = kb.list_content(persona_id=persona_id, status="published")

    # Build simple report
    report = {
        "persona_id": persona_id,
        "period": "last_7_days",
        "stats": {
            "total_published": len(contents),
            "total_drafts": stats.get("draft_contents", 0),
        },
        "top_content": [],
    }

    # Get top content by review score
    sorted_contents = sorted(
        [c for c in contents if c.review_score],
        key=lambda x: x.review_score or 0,
        reverse=True,
    )[:5]

    for content in sorted_contents:
        report["top_content"].append({
            "id": content.id,
            "title": content.title,
            "score": content.review_score,
        })

    return {"success": True, "report": report}


# =============================================================================
# Publish Content Helper
# =============================================================================


async def publish_content(item: PublishQueueItem) -> Dict[str, Any]:
    """
    Publish a queued content item to its platform.

    Args:
        item: PublishQueueItem with content_id and platform

    Returns:
        Dict with success status and post details
    """
    import os
    from avatarfactory.connectors import ConnectorConfig, get_connector
    from avatarfactory.core.knowledge_base import KnowledgeBase

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    # Load content
    # Note: This assumes content is stored in drafts
    contents = kb.list_content(status="draft")
    content = next((c for c in contents if c.id == item.content_id), None)

    if not content:
        return {"success": False, "error": f"Content {item.content_id} not found"}

    # Build connector config from environment
    config = ConnectorConfig()
    platform = item.platform.lower()

    if platform == "bluesky":
        config.username = os.getenv("BLUESKY_USERNAME")
        config.password = os.getenv("BLUESKY_PASSWORD")
    elif platform == "twitter":
        config.api_key = os.getenv("TWITTER_API_KEY")
        config.api_secret = os.getenv("TWITTER_API_SECRET")
        config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    else:
        return {"success": False, "error": f"Unknown platform: {platform}"}

    try:
        connector = get_connector(platform, config)
        await connector.connect()

        # Prepare content text (platform-specific truncation)
        text = content.body
        if platform == "bluesky":
            text = text[:300]
        elif platform == "twitter":
            text = text[:280]

        result = await connector.publish(
            content=text,
            tags=content.tags,
        )

        await connector.disconnect()

        if result.success:
            return {
                "success": True,
                "post_id": result.post_id,
                "post_url": result.post_url,
            }
        else:
            return {"success": False, "error": result.error}

    except Exception as e:
        return {"success": False, "error": str(e)}
