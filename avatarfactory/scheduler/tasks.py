"""
Task Runners for AvatarFactory Scheduler.

Contains implementations for different scheduled task types.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
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
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory

    persona_id = task.persona_id
    platform = task.platform or "bluesky"
    query = task.extra_params.get("query")
    limit = task.extra_params.get("limit", 20)

    if not persona_id:
        return {"success": False, "error": "persona_id required for discovery"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
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
            # Include full data for notification
            "pattern_analysis": data.get("pattern_analysis", {}),
            "ideas": data.get("ideas", []),
        }
    else:
        return {"success": False, "error": result.get("message")}


@TaskRegistry.register("content")
async def run_content_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run content generation task.

    Expected task params:
    - persona_id: str
    - topic: str (optional - will use discovery ideas or content pillars)
    - count: int (default: 1)

    Topic selection priority:
    1. Explicit topic from task params
    2. Unused ideas from recent discovery results
    3. Random pillar/example combination (avoiding recent topics)
    """
    import random
    from avatarfactory.agents.orchestrator import OrchestratorAgent
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory
    from avatarfactory.models.schemas import AgentMessage

    persona_id = task.persona_id
    topic = task.extra_params.get("topic")
    count = task.extra_params.get("count", 1)

    if not persona_id:
        return {"success": False, "error": "persona_id required for content generation"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    # Load persona for notification info
    persona = kb.load_persona(persona_id)
    persona_name = persona.identity.name if persona else ""

    orchestrator = OrchestratorAgent(knowledge_base=kb, llm_provider=provider)

    # If no topic, try to get one from discovery ideas or pillars
    if not topic:
        topic = await _select_topic_for_persona(kb, persona_id, persona)

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
        content_data = data.get("content", {})
        return {
            "success": True,
            "content_id": content_data.get("id"),
            "title": content_data.get("title"),
            # Additional fields for notification
            "body": content_data.get("body", ""),
            "platform": content_data.get("platform", task.platform or ""),
            "persona_name": persona_name,
            "review_score": content_data.get("review_score"),
        }
    else:
        return {"success": False, "error": result.get("message")}


async def _select_topic_for_persona(kb, persona_id: str, persona) -> Optional[str]:
    """
    Select a topic for content generation, avoiding duplicates.

    Priority:
    1. Unused ideas from recent discovery results
    2. Random pillar/example combination (avoiding recent content titles)
    """
    import random

    # Get recent content titles to avoid duplicates
    recent_contents = kb.list_content(persona_id=persona_id, status="draft")
    # Only check the most recent 20
    recent_contents = recent_contents[:20] if len(recent_contents) > 20 else recent_contents
    recent_titles = set()
    recent_topics = set()
    for c in recent_contents:
        if c.title:
            recent_titles.add(c.title.lower())
            # Extract topic keywords (first 5 words)
            words = c.title.lower().split()[:5]
            recent_topics.add(" ".join(words))

    # Try to get ideas from discovery results
    try:
        discovery_results = kb.get_latest_discovery(persona_id)
        if discovery_results:
            ideas = discovery_results.get("ideas", [])
            # Filter out ideas that might be duplicates
            unused_ideas = []
            for idea in ideas:
                idea_topic = idea.get("topic", "") if isinstance(idea, dict) else str(idea)
                idea_lower = idea_topic.lower()
                # Check if this idea is too similar to recent content
                is_duplicate = False
                for recent in recent_topics:
                    if recent in idea_lower or idea_lower in recent:
                        is_duplicate = True
                        break
                if not is_duplicate and idea_topic:
                    unused_ideas.append(idea_topic)

            if unused_ideas:
                # Pick a random unused idea
                return random.choice(unused_ideas)
    except Exception:
        pass  # Discovery results not available

    # Fallback to pillars with randomization
    if persona and persona.content_pillars:
        # Collect all possible topics from all pillars
        all_topics = []
        for pillar in persona.content_pillars:
            if pillar.examples:
                for example in pillar.examples:
                    # Check if not too similar to recent content
                    example_lower = example.lower()
                    is_duplicate = False
                    for recent in recent_topics:
                        if recent in example_lower or example_lower in recent:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        all_topics.append(example)
            else:
                # Generate topic from pillar name
                topic = f"{pillar.name} tips and insights"
                all_topics.append(topic)

        if all_topics:
            return random.choice(all_topics)

        # If all examples are used, generate a variation
        pillar = random.choice(persona.content_pillars)
        variations = [
            f"Latest trends in {pillar.name}",
            f"Common mistakes in {pillar.name}",
            f"Best practices for {pillar.name}",
            f"Beginner's guide to {pillar.name}",
            f"Advanced techniques in {pillar.name}",
            f"Case study: {pillar.name} in action",
            f"Future of {pillar.name}",
        ]
        return random.choice(variations)

    return None


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
    from avatarfactory.core.knowledges import KnowledgeBase

    persona_id = task.persona_id
    if not persona_id:
        return {"success": False, "error": "persona_id required for report"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
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
# Proactive Task Runners
# =============================================================================


def _get_proactive_orchestrator():
    """Get a ProactiveOrchestrator instance for task execution."""
    import os
    from avatarfactory.agents.proactive_orchestrator import ProactiveOrchestrator
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    return ProactiveOrchestrator(knowledge_base=kb, llm_provider=provider)


@TaskRegistry.register("proactive_trending")
async def run_proactive_trending(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run proactive trending scan task.

    Expected task params:
    - persona_id: str
    - platforms: List[str] (optional, defaults to ["bluesky"])
    """
    orchestrator = _get_proactive_orchestrator()
    persona_id = task.persona_id

    if not persona_id:
        return {"success": False, "error": "persona_id required for trending scan"}

    platforms = task.extra_params.get("platforms", [task.platform or "bluesky"])
    result = await orchestrator.run_trending_scan(persona_id, platforms)

    return {
        "success": result.get("status") == "success",
        "platforms": platforms,
        "results": result.get("results", {}),
    }


@TaskRegistry.register("proactive_content")
async def run_proactive_content(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run proactive content suggestions task.

    Expected task params:
    - persona_id: str
    - count: int (optional, defaults to 3)
    """
    orchestrator = _get_proactive_orchestrator()
    persona_id = task.persona_id

    if not persona_id:
        return {"success": False, "error": "persona_id required for content suggestions"}

    count = task.extra_params.get("count", 3)
    result = await orchestrator.generate_content_suggestions(persona_id, count)

    return {
        "success": result.get("status") == "success",
        "suggestions": result.get("suggestions", []),
    }


@TaskRegistry.register("proactive_optimize")
async def run_proactive_optimize(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run proactive persona optimization task.

    Expected task params:
    - persona_id: str
    """
    orchestrator = _get_proactive_orchestrator()
    persona_id = task.persona_id

    if not persona_id:
        return {"success": False, "error": "persona_id required for optimization"}

    feedback = task.extra_params.get("feedback", {})
    result = await orchestrator.run_persona_optimization(persona_id, feedback)

    return {
        "success": result.get("status") == "success",
        "suggestions": result.get("suggestions", []),
        "requires_human_review": result.get("requires_human_review", True),
    }


# =============================================================================
# Evolution Task Runners
# =============================================================================


@TaskRegistry.register("evolution_analysis")
async def run_evolution_analysis(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run evolution analysis task - analyze feedback and generate suggestions.

    Expected task params:
    - persona_id: str
    - period: str (optional, default: "7d")
    """
    import os
    from avatarfactory.agents.evolution import EvolutionAgent
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory

    persona_id = task.persona_id
    period = task.extra_params.get("period", "7d")

    if not persona_id:
        return {"success": False, "error": "persona_id required for evolution analysis"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    agent = EvolutionAgent(knowledge_base=kb, llm_provider=provider)

    try:
        result = await agent.run_scheduled_evolution(persona_id)

        return {
            "success": True,
            "persona_id": persona_id,
            "suggestions_count": result.get("suggestions_count", 0),
            "auto_applied_count": result.get("auto_applied_count", 0),
            "pending_approval": result.get("pending_approval", []),
            # Include analysis summary for notification
            "analysis": result.get("analysis", {}),
        }
    except Exception as e:
        logger.error(f"Evolution analysis failed for {persona_id}: {e}")
        return {"success": False, "error": str(e)}


@TaskRegistry.register("retrospective")
async def run_retrospective(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run retrospective generation task - generate weekly report.

    Expected task params:
    - persona_id: str
    - period: str (optional, default: "weekly")
    """
    import os
    from avatarfactory.agents.evolution import EvolutionAgent
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory

    persona_id = task.persona_id
    period = task.extra_params.get("period", "weekly")

    if not persona_id:
        return {"success": False, "error": "persona_id required for retrospective"}

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    agent = EvolutionAgent(knowledge_base=kb, llm_provider=provider)

    try:
        retrospective = await agent.generate_retrospective(persona_id, period)

        return {
            "success": True,
            "persona_id": persona_id,
            "week": retrospective.get("week"),
            "summary": retrospective.get("summary", {}),
            "what_worked": retrospective.get("what_worked", []),
            "what_didnt": retrospective.get("what_didnt", []),
            "key_insights": retrospective.get("key_insights", []),
        }
    except Exception as e:
        logger.error(f"Retrospective generation failed for {persona_id}: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# System-Level Task Runners (No Persona Required)
# =============================================================================


@TaskRegistry.register("trend_scan")
async def run_trend_scan_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run system-level trend scan across all configured platforms.

    This is a global task that doesn't require a persona - it scans trends
    across platforms and saves snapshots for persona recommendation.

    Expected task params:
    - platforms: List[str] (default: ["bluesky"])
    """
    import os
    import uuid
    from datetime import datetime

    from avatarfactory.connectors import ConnectorConfig, get_connector
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory
    from avatarfactory.models.schemas import TrendSnapshot

    platforms = task.extra_params.get("platforms", ["bluesky"])
    limit = task.extra_params.get("limit", 30)

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    results = {}
    snapshots = []

    for platform in platforms:
        try:
            # Build connector config from environment
            config = ConnectorConfig()
            if platform.lower() == "bluesky":
                config.username = os.getenv("BLUESKY_USERNAME")
                config.password = os.getenv("BLUESKY_PASSWORD")
            elif platform.lower() == "twitter":
                config.api_key = os.getenv("TWITTER_API_KEY")
                config.api_secret = os.getenv("TWITTER_API_SECRET")
                config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
            elif platform.lower() == "xiaohongshu":
                config.cookie = os.getenv("XIAOHONGSHU_COOKIE")
                config.user_id = os.getenv("XIAOHONGSHU_USER_ID")

            connector = get_connector(platform, config)
            await connector.connect()

            # Fetch trending content without specific query (general trending)
            result = await connector.fetch_trending(limit=limit)

            if result.success:
                posts = result.data or []

                # Extract trending topics and hashtags
                topics = set()
                hashtags = set()
                for post in posts:
                    body = post.get("body", "")
                    # Extract hashtags
                    import re
                    tags = re.findall(r"#(\w+)", body)
                    hashtags.update(tags)
                    # Use first line or sentence as topic
                    first_line = body.split("\n")[0][:100]
                    if first_line:
                        topics.add(first_line)

                # Analyze trends with LLM
                analysis = await _analyze_trends_for_snapshot(
                    provider, posts[:20], platform
                )

                # Create snapshot
                snapshot = TrendSnapshot(
                    id=f"snap_{uuid.uuid4().hex[:8]}",
                    platform=platform,
                    captured_at=datetime.now(),
                    trending_topics=list(topics)[:20],
                    trending_hashtags=list(hashtags)[:20],
                    top_posts=posts[:10],
                    analysis_summary=analysis.get("summary", ""),
                    key_themes=analysis.get("themes", []),
                    content_patterns=analysis.get("patterns", []),
                )

                # Save snapshot
                kb.save_trend_snapshot(snapshot)
                snapshots.append(snapshot)

                results[platform] = {
                    "success": True,
                    "post_count": len(posts),
                    "topics_count": len(topics),
                    "hashtags_count": len(hashtags),
                }
            else:
                results[platform] = {
                    "success": False,
                    "error": result.error,
                }

            await connector.disconnect()

        except Exception as e:
            logger.error(f"Trend scan failed for {platform}: {e}")
            results[platform] = {
                "success": False,
                "error": str(e),
            }

    return {
        "success": any(r.get("success") for r in results.values()),
        "platforms_scanned": len(platforms),
        "results": results,
        "snapshots_saved": len(snapshots),
    }


async def _analyze_trends_for_snapshot(
    provider,
    posts: list,
    platform: str,
) -> Dict[str, Any]:
    """Analyze posts to extract themes and patterns for snapshot."""
    if not posts:
        return {"summary": "", "themes": [], "patterns": []}

    # Build posts context
    posts_text = "\n".join([
        f"- {p.get('body', '')[:200]}" for p in posts[:15]
    ])

    prompt = f"""Analyze these trending posts from {platform} and extract:
1. A brief summary of overall trends (2-3 sentences)
2. Key themes (5-10 topics)
3. Content patterns (structural or stylistic patterns)

Posts:
{posts_text}

Return as JSON:
```json
{{
  "summary": "string",
  "themes": ["string"],
  "patterns": ["string"]
}}
```"""

    try:
        response = await provider.generate(
            prompt=prompt,
            system="You are a social media trend analyst. Extract key trends and patterns.",
            temperature=0.5,
            max_tokens=1024,
        )

        # Parse JSON
        import json
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response

        return json.loads(json_str)
    except Exception as e:
        logger.warning(f"Trend analysis failed: {e}")
        return {"summary": "", "themes": [], "patterns": []}


@TaskRegistry.register("persona_recommendation")
async def run_persona_recommendation_task(task: ScheduledTask) -> Dict[str, Any]:
    """
    Run persona recommendation task - generates recommended personas from trends.

    This is a system-level task that reads today's trend snapshots and
    generates persona recommendations.

    Expected task params:
    - count: int (default: 3)
    """
    import os

    from avatarfactory.agents.recommendation import RecommendationAgent
    from avatarfactory.core.knowledges import KnowledgeBase
    from avatarfactory.core.llm_provider import LLMProviderFactory

    count = task.extra_params.get("count", 3)

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = KnowledgeBase(kb_path)
    provider = LLMProviderFactory.from_env()

    # Get today's trend snapshots
    snapshots = kb.get_today_trend_snapshots()

    if not snapshots:
        # Fallback: get latest snapshots
        snapshots = kb.get_latest_trend_snapshots(limit=5)

    if not snapshots:
        return {
            "success": False,
            "error": "No trend snapshots available. Run trend_scan first.",
        }

    # Generate recommendations
    agent = RecommendationAgent(knowledge_base=kb, llm_provider=provider)
    recommendations = await agent.generate_recommendations(snapshots, count)

    if recommendations:
        # Save recommendations
        kb.save_recommended_personas(recommendations)

        return {
            "success": True,
            "recommendations_count": len(recommendations),
            "recommendations": [
                {
                    "id": r.id,
                    "name": r.name,
                    "domain": r.domain,
                    "tagline": r.tagline,
                    "relevance_score": r.relevance_score,
                    "potential_score": r.potential_score,
                }
                for r in recommendations
            ],
        }
    else:
        return {
            "success": False,
            "error": "Failed to generate recommendations",
        }


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
    from avatarfactory.core.knowledges import KnowledgeBase

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
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
