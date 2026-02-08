"""
Proactive Orchestrator Agent for AvatarFactory.

Extends OrchestratorAgent with proactive task scheduling and
automated discovery/content generation workflows.
"""

from typing import Any, Dict, List, Optional

from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.agents.discovery import DiscoveryAgent
from avatarfactory.models.schemas import AgentMessage, TaskType


class ProactiveOrchestrator(OrchestratorAgent):
    """
    Enhanced orchestrator with proactive task scheduling capabilities.

    Extends OrchestratorAgent to support:
    - Scheduled discovery and content generation tasks
    - Automated persona optimization suggestions
    - Proactive content planning
    """

    def __init__(self, *args: Any, scheduler: Optional[Any] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._scheduler = scheduler
        self._discovery_agent: Optional[DiscoveryAgent] = None

    @property
    def discovery_agent(self) -> DiscoveryAgent:
        """Lazily initialize and return DiscoveryAgent."""
        if self._discovery_agent is None:
            self._discovery_agent = DiscoveryAgent(
                knowledge_base=self.kb,
                llm_provider=self.llm_provider,
            )
        return self._discovery_agent

    @property
    def scheduler(self) -> Optional[Any]:
        """Get the scheduler instance."""
        return self._scheduler

    def set_scheduler(self, scheduler: Any) -> None:
        """Set the scheduler instance."""
        self._scheduler = scheduler

    # =========================================================================
    # Proactive Task Management
    # =========================================================================

    async def setup_persona_tasks(
        self,
        persona_id: str,
        discovery_platforms: Optional[List[str]] = None,
        content_platforms: Optional[List[str]] = None,
        discovery_schedule: Optional[str] = None,
        content_schedule: Optional[str] = None,
        evolution_schedule: Optional[str] = None,
        enable_evolution: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Set up proactive scheduled tasks for a persona.

        Creates:
        - Discovery task: scan for trending topics
        - Content task: generate content suggestions
        - Evolution task: analyze feedback and generate suggestions (optional)

        Args:
            persona_id: Persona ID to set up tasks for
            discovery_platforms: Platforms for discovery/trending scan (defaults to ["bluesky"])
            content_platforms: Platforms for content generation (defaults to ["xiaohongshu"])
            discovery_schedule: Custom cron schedule for discovery (default: "0 */6 * * *")
            content_schedule: Custom cron schedule for content generation (default: "0 9 * * *")
            evolution_schedule: Custom cron schedule for evolution analysis (default: "0 8 * * 0")
            enable_evolution: Whether to enable evolution tasks (default: True)

        Returns:
            List of created task configurations
        """
        if not self._scheduler:
            self.log("WARNING", "No scheduler configured, cannot set up persona tasks")
            return []

        # Get persona name for task naming
        persona = self.kb.load_persona(persona_id)
        persona_name = persona.identity.name if persona else persona_id[:12]

        discovery_platforms = discovery_platforms or ["bluesky"]
        content_platforms = content_platforms or ["xiaohongshu"]
        discovery_schedule = discovery_schedule or "0 */6 * * *"
        content_schedule = content_schedule or "0 9 * * *"
        evolution_schedule = evolution_schedule or "0 8 * * 0"  # Weekly on Sunday 8:00
        tasks = []

        # Discovery task (only if discovery platforms specified)
        if discovery_platforms:
            discovery_task = {
                "id": f"discovery_{persona_id}",
                "name": f"Discovery - {persona_name}",
                "task_type": "discovery",
                "schedule": discovery_schedule,
                "persona_id": persona_id,
                "extra_params": {"platforms": discovery_platforms},
            }
            tasks.append(discovery_task)

        # Content task (only if content platforms specified)
        if content_platforms:
            content_task = {
                "id": f"content_{persona_id}",
                "name": f"Content - {persona_name}",
                "task_type": "content",
                "schedule": content_schedule,
                "persona_id": persona_id,
                "extra_params": {"count": 3, "platforms": content_platforms},
            }
            tasks.append(content_task)

        # Evolution task (analyze feedback and generate suggestions)
        if enable_evolution:
            evolution_task = {
                "id": f"evolution_{persona_id}",
                "name": f"Evolution - {persona_name}",
                "task_type": "evolution_analysis",
                "schedule": evolution_schedule,
                "persona_id": persona_id,
                "extra_params": {"period": "7d"},
            }
            tasks.append(evolution_task)

        # Add tasks to scheduler - collect all tasks first, then add in batch
        created_tasks = []
        for task in tasks:
            try:
                self._scheduler.add_task_from_dict(task, save_state=False)
                created_tasks.append(task)
                self.log("INFO", f"Added task: {task['name']} for {persona_id}")
            except Exception as e:
                self.log("ERROR", f"Failed to add task {task['name']}: {e}")

        # Save state once after all tasks are added
        if created_tasks:
            self._scheduler.save_state()

        return created_tasks

    async def remove_persona_tasks(self, persona_id: str) -> int:
        """
        Remove all proactive tasks for a persona.

        Args:
            persona_id: Persona ID

        Returns:
            Number of tasks removed
        """
        if not self._scheduler:
            return 0

        task_ids = [
            f"discovery_{persona_id}",
            f"content_{persona_id}",
            # Also try old task IDs for backward compatibility
            f"trending_{persona_id}",
            f"content_suggest_{persona_id}",
            f"optimize_{persona_id}",
        ]

        removed = 0
        for task_id in task_ids:
            try:
                if self._scheduler.remove_task(task_id):
                    removed += 1
            except Exception:
                pass

        self.log("INFO", f"Removed {removed} proactive tasks for {persona_id}")
        return removed

    # =========================================================================
    # Proactive Task Runners
    # =========================================================================

    async def run_trending_scan(
        self,
        persona_id: str,
        platforms: List[str],
    ) -> Dict[str, Any]:
        """
        Execute a trending scan for a persona.

        Args:
            persona_id: Persona ID
            platforms: List of platforms to scan

        Returns:
            Dict with scan results
        """
        self.log("INFO", f"Running trending scan for {persona_id} on {platforms}")

        results = {}
        for platform in platforms:
            try:
                result = await self.discovery_agent.discover_and_analyze(
                    persona_id=persona_id,
                    platform=platform,
                    limit=30,
                )
                results[platform] = {
                    "status": result.get("status"),
                    "trending_count": result.get("data", {}).get("trending_count", 0),
                    "ideas_count": len(result.get("data", {}).get("ideas", [])),
                }
            except Exception as e:
                self.log("ERROR", f"Trending scan failed for {platform}: {e}")
                results[platform] = {"status": "error", "error": str(e)}

        # Save results to knowledges
        try:
            self.kb.save_discovery_results(persona_id, results)
        except Exception as e:
            self.log("WARNING", f"Failed to save discovery results: {e}")

        return {
            "status": "success",
            "persona_id": persona_id,
            "platforms": platforms,
            "results": results,
        }

    async def generate_content_suggestions(
        self,
        persona_id: str,
        count: int = 3,
    ) -> Dict[str, Any]:
        """
        Generate content suggestions based on recent discoveries.

        Args:
            persona_id: Persona ID
            count: Number of suggestions to generate

        Returns:
            Dict with content suggestions
        """
        self.log("INFO", f"Generating content suggestions for {persona_id}")

        # Try to get latest discovery results
        try:
            trends = self.kb.get_latest_discovery(persona_id)
        except Exception:
            trends = None

        if trends:
            ideas = trends.get("ideas", [])[:count]
            return {
                "status": "success",
                "persona_id": persona_id,
                "suggestions": ideas,
                "from_cache": True,
            }

        # If no cached results, run a fresh discovery
        try:
            result = await self.discovery_agent.discover_and_analyze(
                persona_id=persona_id,
                platform="bluesky",
                limit=20,
            )

            if result.get("status") == "success":
                ideas = result.get("data", {}).get("ideas", [])[:count]
                return {
                    "status": "success",
                    "persona_id": persona_id,
                    "suggestions": ideas,
                    "from_cache": False,
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("message", "Discovery failed"),
                }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def run_persona_optimization(
        self,
        persona_id: str,
        feedback: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate persona optimization suggestions.

        Args:
            persona_id: Persona ID
            feedback: Optional user feedback to incorporate

        Returns:
            Dict with optimization suggestions
        """
        self.log("INFO", f"Running persona optimization for {persona_id}")

        # Gather performance data
        performance = self._gather_performance_data(persona_id)

        # Get latest trends
        try:
            trends = self.kb.get_latest_discovery(persona_id)
        except Exception:
            trends = None

        # Generate suggestions
        try:
            suggestions = await self.persona_agent.suggest_optimizations(
                persona_id,
                {
                    "performance": performance,
                    "trends": trends,
                    "feedback": feedback or {},
                },
            )

            return {
                "status": "success",
                "persona_id": persona_id,
                "suggestions": suggestions,
                "requires_human_review": True,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _gather_performance_data(self, persona_id: str) -> Dict[str, Any]:
        """Gather performance metrics for a persona."""
        try:
            published = self.kb.list_content(persona_id=persona_id, status="published")
            drafts = self.kb.list_content(persona_id=persona_id, status="draft")

            # Calculate basic metrics
            total_published = len(published)
            total_drafts = len(drafts)

            # Content by pillar
            pillar_counts: Dict[str, int] = {}
            for content in published:
                pillar = content.pillar
                pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1

            # Average review scores
            reviewed_content = [c for c in drafts if c.review_score]
            avg_score = (
                sum(c.review_score for c in reviewed_content) / len(reviewed_content)
                if reviewed_content
                else 0
            )

            return {
                "total_published": total_published,
                "total_drafts": total_drafts,
                "content_by_pillar": pillar_counts,
                "avg_review_score": avg_score,
            }

        except Exception as e:
            self.log("WARNING", f"Failed to gather performance data: {e}")
            return {}
