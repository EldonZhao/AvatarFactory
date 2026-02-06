"""
Data providers for the dashboard.

Provides unified access to knowledges, scheduler, and connector data
for visualization in the Streamlit dashboard.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.connectors.registry import ConnectorRegistry
from avatarfactory.scheduler.engine import Scheduler, SchedulerConfig, ScheduledTask


@dataclass
class TopologyNode:
    """Node in the system topology graph."""
    id: str
    label: str
    node_type: str  # persona, agent, connector, task, content
    size: int = 25
    color: str = "#4A90D9"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TopologyEdge:
    """Edge connecting two nodes in the topology."""
    source: str
    target: str
    label: str = ""
    color: str = "#888888"


@dataclass
class PersonaSummary:
    """Summary of a persona for dashboard display."""
    id: str
    name: str
    tagline: str
    platforms: List[str]
    version: str
    created_at: Optional[datetime]
    draft_count: int = 0
    published_count: int = 0
    notification_enabled: bool = False
    notification_type: str = ""


@dataclass
class ConnectorStatus:
    """Status of a platform connector."""
    platform: str
    registered: bool
    configured: bool
    config_keys: List[str]


class DashboardDataProvider:
    """
    Unified data provider for the dashboard.

    Aggregates data from Knowledges, Scheduler, and ConnectorRegistry
    for display in the Streamlit dashboard.
    """

    def __init__(self, kb_path: Optional[str] = None):
        """Initialize the data provider."""
        self.kb_path = kb_path or os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
        self.kb = KnowledgeBase(self.kb_path)

        scheduler_dir = os.path.join(self.kb_path, "scheduler")
        self.scheduler = Scheduler(SchedulerConfig(data_dir=scheduler_dir))

    def get_personas(self) -> List[PersonaSummary]:
        """Get all personas with summary information."""
        personas = []
        for persona_id in self.kb.list_personas():
            persona = self.kb.load_persona(persona_id)
            if persona:
                draft_count = len(self.kb.list_content(persona_id, status="draft"))
                published_count = len(self.kb.list_content(persona_id, status="published"))

                # Get notification config
                notification_enabled = False
                notification_type = ""
                if persona.notification:
                    notification_enabled = persona.notification.enabled
                    notification_type = persona.notification.connector_type if notification_enabled else ""

                personas.append(PersonaSummary(
                    id=persona.id,
                    name=persona.identity.name,
                    tagline=persona.identity.tagline,
                    platforms=[p.value for p in persona.platforms],
                    version=persona.version,
                    created_at=persona.created_at,
                    draft_count=draft_count,
                    published_count=published_count,
                    notification_enabled=notification_enabled,
                    notification_type=notification_type,
                ))
        return personas

    def get_persona_details(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get full persona details."""
        persona = self.kb.load_persona(persona_id)
        if not persona:
            return None
        return persona.model_dump(mode="json")

    def get_content_list(
        self,
        persona_id: Optional[str] = None,
        status: str = "draft",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get content list with key information."""
        contents = self.kb.list_content(persona_id=persona_id, status=status)[:limit]
        return [
            {
                "id": c.id,
                "title": c.title,
                "persona_id": c.persona_id,
                "platform": c.platform.value,
                "pillar": c.pillar,
                "review_score": c.review_score,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "tags": c.tags[:5],  # First 5 tags
            }
            for c in contents
        ]

    def get_content_details(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get full content details."""
        content = self.kb.load_content(content_id, status="draft")
        if not content:
            content = self.kb.load_content(content_id, status="published")
        if not content:
            return None
        return content.model_dump(mode="json")

    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks with status."""
        tasks = self.scheduler.list_tasks()
        return [
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
                "run_count": t.run_count,
            }
            for t in tasks
        ]

    def get_next_runs(self) -> List[Dict[str, Any]]:
        """Get next scheduled run times."""
        return self.scheduler.get_next_runs()

    def get_connector_statuses(self) -> List[ConnectorStatus]:
        """Get status of all connectors."""
        # Define expected configuration for each platform
        platform_configs = {
            "bluesky": {
                "env_keys": ["BLUESKY_USERNAME", "BLUESKY_PASSWORD"],
            },
            "twitter": {
                "env_keys": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN"],
            },
            "xiaohongshu": {
                "env_keys": ["XIAOHONGSHU_COOKIE"],
            },
            "wecom": {
                "env_keys": ["AVATARFACTORY_WEBHOOK_URL"],
            },
        }

        statuses = []
        for platform, config in platform_configs.items():
            registered = ConnectorRegistry.is_registered(platform)
            configured = all(
                os.getenv(key) is not None
                for key in config["env_keys"]
            )
            missing = [k for k in config["env_keys"] if not os.getenv(k)]

            statuses.append(ConnectorStatus(
                platform=platform,
                registered=registered,
                configured=configured,
                config_keys=missing if not configured else [],
            ))

        return statuses

    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        return self.kb.get_storage_stats()

    def get_topology_data(self) -> Dict[str, List]:
        """
        Build topology graph data for visualization.

        Returns nodes and edges representing the system architecture:
        - Personas connected to agents
        - Agents connected to connectors
        - Tasks connected to personas
        """
        nodes: List[TopologyNode] = []
        edges: List[TopologyEdge] = []

        # Color scheme
        colors = {
            "persona": "#4A90D9",      # Blue
            "agent": "#7B68EE",        # Purple
            "connector": "#50C878",    # Green
            "task": "#FFB347",         # Orange
            "content": "#87CEEB",      # Light blue
        }

        # Add agent nodes (central system)
        agents = [
            ("orchestrator", "Orchestrator"),
            ("persona_agent", "Persona Agent"),
            ("content_agent", "Content Agent"),
            ("discovery_agent", "Discovery Agent"),
            ("review_agent", "Review Agent"),
        ]
        for agent_id, agent_name in agents:
            nodes.append(TopologyNode(
                id=agent_id,
                label=agent_name,
                node_type="agent",
                size=30,
                color=colors["agent"],
            ))

        # Orchestrator connects to all agents
        for agent_id, _ in agents[1:]:
            edges.append(TopologyEdge(
                source="orchestrator",
                target=agent_id,
                label="manages",
            ))

        # Add persona nodes
        personas = self.get_personas()
        for p in personas:
            nodes.append(TopologyNode(
                id=f"persona_{p.id}",
                label=p.name,
                node_type="persona",
                size=35,
                color=colors["persona"],
                metadata={"draft": p.draft_count, "published": p.published_count},
            ))
            # Personas connect to persona agent
            edges.append(TopologyEdge(
                source="persona_agent",
                target=f"persona_{p.id}",
                label="manages",
            ))

        # Add connector nodes
        connector_statuses = self.get_connector_statuses()
        for status in connector_statuses:
            node_color = colors["connector"] if status.configured else "#CCCCCC"
            nodes.append(TopologyNode(
                id=f"connector_{status.platform}",
                label=status.platform.capitalize(),
                node_type="connector",
                size=25,
                color=node_color,
            ))
            # Discovery agent connects to connectors
            edges.append(TopologyEdge(
                source="discovery_agent",
                target=f"connector_{status.platform}",
                label="fetches from",
            ))

        # Add task nodes
        tasks = self.get_scheduled_tasks()
        for t in tasks[:10]:  # Limit to 10 tasks for clarity
            task_color = colors["task"] if t["enabled"] else "#CCCCCC"
            nodes.append(TopologyNode(
                id=f"task_{t['id']}",
                label=t["name"][:20],
                node_type="task",
                size=20,
                color=task_color,
            ))
            # Tasks connect to personas
            if t.get("persona_id"):
                edges.append(TopologyEdge(
                    source=f"task_{t['id']}",
                    target=f"persona_{t['persona_id']}",
                    label="targets",
                ))

        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type,
                    "size": n.size,
                    "color": n.color,
                    "metadata": n.metadata,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "label": e.label,
                    "color": e.color,
                }
                for e in edges
            ],
        }
