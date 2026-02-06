"""
Knowledge Base - Data storage and retrieval layer.

Handles persistence of personas, content, experiments, and other data.
Uses file-based storage (YAML/JSON) for MVP, can be extended to database later.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from avatarfactory.models.schemas import (
    Content,
    Experiment,
    Persona,
    PersonaVersion,
    ReviewReport,
    SimulationReport,
    WeeklyRetrospective,
)


class KnowledgeBase:
    """Knowledge base for storing and retrieving all AvatarFactory data"""

    def __init__(self, base_path: str = "./knowledges"):
        self.base_path = Path(base_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure knowledge base directory structure exists"""
        dirs = [
            self.base_path / "personas",
            self.base_path / "content_library" / "published",
            self.base_path / "content_library" / "drafts",
            self.base_path / "content_library" / "templates",
            self.base_path / "experiments",
            self.base_path / "platform_rules",
            self.base_path / "user_feedback" / "comments",
            self.base_path / "user_feedback" / "dms",
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # Persona Management
    # ========================================================================

    def save_persona(self, persona: Persona) -> None:
        """Save or update a persona"""
        persona_dir = self.base_path / "personas" / persona.id
        persona_dir.mkdir(parents=True, exist_ok=True)

        # Save current config (use mode='json' to serialize enums as strings)
        config_path = persona_dir / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(persona.model_dump(mode='json'), f, allow_unicode=True, sort_keys=False)

        # Save to versions directory
        versions_dir = persona_dir / "versions"
        versions_dir.mkdir(exist_ok=True)
        version_path = versions_dir / f"{persona.version}.yaml"
        with open(version_path, "w", encoding="utf-8") as f:
            yaml.dump(persona.model_dump(mode='json'), f, allow_unicode=True, sort_keys=False)

    def load_persona(self, persona_id: str) -> Optional[Persona]:
        """Load a persona by ID"""
        config_path = self.base_path / "personas" / persona_id / "config.yaml"
        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Persona(**data)

    def list_personas(self, sort_by_created: bool = True) -> List[str]:
        """List all persona IDs, optionally sorted by creation time (newest first)."""
        personas_dir = self.base_path / "personas"
        if not personas_dir.exists():
            return []

        persona_dirs = [d for d in personas_dir.iterdir() if d.is_dir()]

        if not sort_by_created:
            return [d.name for d in persona_dirs]

        # Sort by creation time from config.yaml
        def get_created_time(persona_dir):
            config_path = persona_dir / "config.yaml"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    created_at = data.get("created_at", "")
                    if created_at:
                        return created_at
                except Exception:
                    pass
            # Fallback to directory modification time
            return persona_dir.stat().st_mtime

        # Sort by created_at descending (newest first)
        sorted_dirs = sorted(persona_dirs, key=get_created_time, reverse=True)
        return [d.name for d in sorted_dirs]

    def save_persona_version(self, persona_id: str, version_info: PersonaVersion) -> None:
        """Save persona version history record"""
        persona_dir = self.base_path / "personas" / persona_id
        history_path = persona_dir / "history.json"

        # Load existing history
        history = []
        if history_path.exists():
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)

        # Add new version
        history.append(version_info.model_dump(mode="json"))

        # Save
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_persona_history(self, persona_id: str) -> List[PersonaVersion]:
        """Get persona version history"""
        history_path = self.base_path / "personas" / persona_id / "history.json"
        if not history_path.exists():
            return []

        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [PersonaVersion(**item) for item in data]

    def delete_persona(self, persona_id: str, delete_content: bool = True) -> Dict[str, Any]:
        """
        Delete a persona and optionally all associated data.

        Args:
            persona_id: The persona ID to delete
            delete_content: If True, also delete all content created by this persona

        Returns:
            Dict with deletion summary:
            - persona_deleted: bool
            - content_deleted: int (count of deleted content files)
            - discovery_deleted: bool
            - errors: List[str] (any errors encountered)
        """
        result = {
            "persona_deleted": False,
            "content_deleted": 0,
            "discovery_deleted": False,
            "errors": [],
        }

        # 1. Check if persona exists
        persona_dir = self.base_path / "personas" / persona_id
        if not persona_dir.exists():
            result["errors"].append(f"Persona {persona_id} not found")
            return result

        # 2. Delete associated content (drafts and published)
        if delete_content:
            for folder in ["drafts", "published"]:
                content_dir = self.base_path / "content_library" / folder
                if content_dir.exists():
                    for file_path in content_dir.glob("*.json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            if data.get("persona_id") == persona_id:
                                file_path.unlink()
                                result["content_deleted"] += 1
                        except Exception as e:
                            result["errors"].append(f"Failed to delete {file_path}: {e}")

        # 3. Delete persona directory (includes discovery data, reviews, versions)
        try:
            shutil.rmtree(persona_dir)
            result["persona_deleted"] = True
            result["discovery_deleted"] = True  # Discovery is inside persona dir
        except Exception as e:
            result["errors"].append(f"Failed to delete persona directory: {e}")

        return result

    # ========================================================================
    # Content Management
    # ========================================================================

    def save_content(self, content: Content, status: str = "draft") -> None:
        """Save content (draft or published)"""
        folder = "drafts" if status == "draft" else "published"
        content_dir = self.base_path / "content_library" / folder
        content_dir.mkdir(parents=True, exist_ok=True)

        # Filename: {date}_{id}.json
        date_str = content.created_at.strftime("%Y-%m-%d")
        filename = f"{date_str}_{content.id}.json"
        content_path = content_dir / filename

        with open(content_path, "w", encoding="utf-8") as f:
            json.dump(content.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_content(self, content_id: str, status: str = "draft") -> Optional[Content]:
        """Load content by ID"""
        folder = "drafts" if status == "draft" else "published"
        content_dir = self.base_path / "content_library" / folder

        # Search for file containing content_id
        for file_path in content_dir.glob(f"*_{content_id}.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Content(**data)
        return None

    def list_content(
        self, persona_id: Optional[str] = None, status: str = "draft"
    ) -> List[Content]:
        """List content, optionally filtered by persona_id"""
        folder = "drafts" if status == "draft" else "published"
        content_dir = self.base_path / "content_library" / folder

        contents = []
        for file_path in content_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            content = Content(**data)
            if persona_id is None or content.persona_id == persona_id:
                contents.append(content)

        return sorted(contents, key=lambda c: c.created_at, reverse=True)

    def move_to_published(self, content_id: str) -> bool:
        """Move content from draft to published"""
        content = self.load_content(content_id, status="draft")
        if not content:
            return False

        # Save to published
        self.save_content(content, status="published")

        # Delete from drafts
        content_dir = self.base_path / "content_library" / "drafts"
        for file_path in content_dir.glob(f"*_{content_id}.json"):
            file_path.unlink()

        return True

    # ========================================================================
    # Review Reports
    # ========================================================================

    def save_review_report(self, report: ReviewReport, persona_id: str) -> None:
        """Save review report"""
        persona_dir = self.base_path / "personas" / persona_id
        reviews_dir = persona_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)

        report_path = reviews_dir / f"{report.content_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_review_report(
        self, content_id: str, persona_id: str
    ) -> Optional[ReviewReport]:
        """Load review report"""
        report_path = (
            self.base_path / "personas" / persona_id / "reviews" / f"{content_id}.json"
        )
        if not report_path.exists():
            return None

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ReviewReport(**data)

    # ========================================================================
    # Simulation Reports
    # ========================================================================

    def save_simulation_report(
        self, report: SimulationReport, persona_id: str
    ) -> None:
        """Save simulation report"""
        persona_dir = self.base_path / "personas" / persona_id
        simulations_dir = persona_dir / "simulations"
        simulations_dir.mkdir(exist_ok=True)

        report_path = simulations_dir / f"{report.content_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_simulation_report(
        self, content_id: str, persona_id: str
    ) -> Optional[SimulationReport]:
        """Load simulation report"""
        report_path = (
            self.base_path
            / "personas"
            / persona_id
            / "simulations"
            / f"{content_id}.json"
        )
        if not report_path.exists():
            return None

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SimulationReport(**data)

    # ========================================================================
    # Experiments
    # ========================================================================

    def save_experiment(self, experiment: Experiment) -> None:
        """Save experiment"""
        exp_dir = self.base_path / "experiments" / experiment.id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Save experiment data
        exp_path = exp_dir / "experiment.json"
        with open(exp_path, "w", encoding="utf-8") as f:
            json.dump(experiment.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Load experiment"""
        exp_path = self.base_path / "experiments" / experiment_id / "experiment.json"
        if not exp_path.exists():
            return None

        with open(exp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Experiment(**data)

    def list_experiments(self, persona_id: Optional[str] = None) -> List[Experiment]:
        """List experiments, optionally filtered by persona_id"""
        experiments_dir = self.base_path / "experiments"
        if not experiments_dir.exists():
            return []

        experiments = []
        for exp_dir in experiments_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            exp_path = exp_dir / "experiment.json"
            if exp_path.exists():
                with open(exp_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                exp = Experiment(**data)
                if persona_id is None or exp.persona_id == persona_id:
                    experiments.append(exp)

        return sorted(experiments, key=lambda e: e.created_at, reverse=True)

    # ========================================================================
    # Retrospectives
    # ========================================================================

    def save_retrospective(self, retro: WeeklyRetrospective) -> None:
        """Save weekly retrospective"""
        persona_dir = self.base_path / "personas" / retro.persona_id
        retros_dir = persona_dir / "retrospectives"
        retros_dir.mkdir(exist_ok=True)

        retro_path = retros_dir / f"{retro.week}.json"
        with open(retro_path, "w", encoding="utf-8") as f:
            json.dump(retro.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_retrospective(
        self, week: str, persona_id: str
    ) -> Optional[WeeklyRetrospective]:
        """Load retrospective by week"""
        retro_path = (
            self.base_path / "personas" / persona_id / "retrospectives" / f"{week}.json"
        )
        if not retro_path.exists():
            return None

        with open(retro_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return WeeklyRetrospective(**data)

    def list_retrospectives(self, persona_id: str) -> List[WeeklyRetrospective]:
        """List all retrospectives for a persona"""
        retros_dir = self.base_path / "personas" / persona_id / "retrospectives"
        if not retros_dir.exists():
            return []

        retros = []
        for retro_path in retros_dir.glob("*.json"):
            with open(retro_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            retros.append(WeeklyRetrospective(**data))

        return sorted(retros, key=lambda r: r.week, reverse=True)

    # ========================================================================
    # Platform Rules
    # ========================================================================

    def save_platform_rules(self, platform: str, rules: Dict[str, Any]) -> None:
        """Save platform-specific rules"""
        platform_dir = self.base_path / "platform_rules" / platform
        platform_dir.mkdir(parents=True, exist_ok=True)

        rules_path = platform_dir / "rules.yaml"
        with open(rules_path, "w", encoding="utf-8") as f:
            yaml.dump(rules, f, allow_unicode=True, sort_keys=False)

    def load_platform_rules(self, platform: str) -> Optional[Dict[str, Any]]:
        """Load platform-specific rules"""
        rules_path = self.base_path / "platform_rules" / platform / "rules.yaml"
        if not rules_path.exists():
            return None

        with open(rules_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ========================================================================
    # Utilities
    # ========================================================================

    def export_persona_data(self, persona_id: str, export_path: str) -> None:
        """Export all data for a persona to a zip file"""
        persona_dir = self.base_path / "personas" / persona_id
        if not persona_dir.exists():
            raise ValueError(f"Persona {persona_id} not found")

        shutil.make_archive(export_path, "zip", persona_dir)

    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics"""
        return {
            "total_personas": len(self.list_personas()),
            "draft_contents": len(self.list_content(status="draft")),
            "published_contents": len(self.list_content(status="published")),
            "total_experiments": len(self.list_experiments()),
        }

    # ========================================================================
    # Discovery Results (Trending Data)
    # ========================================================================

    def save_discovery_results(
        self,
        persona_id: str,
        platform: str,
        results: Dict[str, Any],
    ) -> None:
        """
        Save discovery/trending results for a persona.

        Args:
            persona_id: Persona ID
            platform: Platform name (e.g., "bluesky", "twitter")
            results: Discovery results including patterns and ideas
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"
        discovery_dir.mkdir(parents=True, exist_ok=True)

        # Save platform-specific results
        result_path = discovery_dir / f"{platform}.json"
        data = {
            "platform": platform,
            "updated_at": datetime.now().isoformat(),
            **results,
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_latest_discovery(
        self,
        persona_id: str,
        platform: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest discovery results for a persona.

        Args:
            persona_id: Persona ID
            platform: Platform name (optional, returns first available if not specified)

        Returns:
            Discovery results or None if not found
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"

        if not discovery_dir.exists():
            return None

        if platform:
            result_path = discovery_dir / f"{platform}.json"
            if result_path.exists():
                with open(result_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        else:
            # Return first available platform's results
            for result_path in discovery_dir.glob("*.json"):
                with open(result_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None

    def list_discovery_platforms(self, persona_id: str) -> List[str]:
        """
        List platforms with discovery results for a persona.

        Args:
            persona_id: Persona ID

        Returns:
            List of platform names
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"

        if not discovery_dir.exists():
            return []

        return [p.stem for p in discovery_dir.glob("*.json")]
