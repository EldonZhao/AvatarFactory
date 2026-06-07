"""
Knowledges - Data storage and retrieval layer.

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
    EvolutionSuggestion,
    EvolutionFeedbackAnalysis,
    AgentConfig,
    RecommendedPersona,
    TrendSnapshot,
)


class KnowledgeBase:
    """Knowledges storage for all AvatarFactory data"""

    def __init__(self, base_path: str = "./knowledges"):
        self.base_path = Path(base_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure knowledges directory structure exists"""
        dirs = [
            self.base_path / "personas",
            self.base_path / "content_library" / "published",
            self.base_path / "content_library" / "drafts",
            self.base_path / "content_library" / "templates",
            self.base_path / "experiments",
            self.base_path / "platform_rules",
            self.base_path / "user_feedback" / "comments",
            self.base_path / "user_feedback" / "dms",
            self.base_path / "recommendations" / "personas",
            self.base_path / "recommendations" / "trends",
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
            yaml.dump(persona.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False)

        # Save to versions directory
        versions_dir = persona_dir / "versions"
        versions_dir.mkdir(exist_ok=True)
        version_path = versions_dir / f"{persona.version}.yaml"
        with open(version_path, "w", encoding="utf-8") as f:
            yaml.dump(persona.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False)

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
            - discovery_deleted: int (count of deleted discovery files)
            - errors: List[str] (any errors encountered)
        """
        result = {
            "persona_deleted": False,
            "content_deleted": 0,
            "discovery_deleted": 0,
            "errors": [],
        }

        # 1. Check if persona exists
        persona_dir = self.base_path / "personas" / persona_id
        if not persona_dir.exists():
            result["errors"].append(f"Persona {persona_id} not found")
            return result

        # 2. Count content and discovery files before deletion
        if delete_content:
            # Count content in persona directory (new structure)
            for folder in ["drafts", "published"]:
                content_dir = persona_dir / "content" / folder
                if content_dir.exists():
                    result["content_deleted"] += len(list(content_dir.glob("*.json")))

            # Also clean legacy content_library location
            for folder in ["drafts", "published"]:
                legacy_dir = self.base_path / "content_library" / folder
                if legacy_dir.exists():
                    for file_path in legacy_dir.glob("*.json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            if data.get("persona_id") == persona_id:
                                file_path.unlink()
                                result["content_deleted"] += 1
                        except Exception as e:
                            result["errors"].append(
                                f"Failed to delete legacy content {file_path}: {e}"
                            )

        # Count discovery files
        discovery_dir = persona_dir / "discovery"
        if discovery_dir.exists():
            result["discovery_deleted"] = len(list(discovery_dir.glob("*.json")))

        # 3. Delete persona directory (includes content, discovery, reviews, versions)
        try:
            shutil.rmtree(persona_dir)
            result["persona_deleted"] = True
        except Exception as e:
            result["errors"].append(f"Failed to delete persona directory: {e}")

        return result

    # ========================================================================
    # Content Management
    # ========================================================================

    def _get_content_dir(self, persona_id: str, status: str = "draft") -> Path:
        """Get content directory for a persona."""
        folder = "drafts" if status == "draft" else "published"
        content_dir = self.base_path / "personas" / persona_id / "content" / folder
        content_dir.mkdir(parents=True, exist_ok=True)
        return content_dir

    def save_content(self, content: Content, status: str = "draft") -> None:
        """Save content under persona directory with timestamp."""
        persona_id = content.persona_id
        if not persona_id:
            raise ValueError("Content must have persona_id")

        content_dir = self._get_content_dir(persona_id, status)

        # Filename: {datetime}_{id}.json (e.g., 2026-02-06_12-04_content_xxx.json)
        datetime_str = content.created_at.strftime("%Y-%m-%d_%H-%M")
        filename = f"{datetime_str}_{content.id}.json"
        content_path = content_dir / filename

        with open(content_path, "w", encoding="utf-8") as f:
            json.dump(content.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_content(self, content_id: str, status: str = "draft") -> Optional[Content]:
        """Load content by ID, searching across all personas."""
        # First, try to find in persona directories (new structure)
        personas_dir = self.base_path / "personas"
        if personas_dir.exists():
            for persona_dir in personas_dir.iterdir():
                if not persona_dir.is_dir():
                    continue
                folder = "drafts" if status == "draft" else "published"
                content_dir = persona_dir / "content" / folder
                if content_dir.exists():
                    for file_path in content_dir.glob(f"*_{content_id}.json"):
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        return Content(**data)

        # Fallback: try legacy content_library location
        folder = "drafts" if status == "draft" else "published"
        legacy_dir = self.base_path / "content_library" / folder
        if legacy_dir.exists():
            for file_path in legacy_dir.glob(f"*_{content_id}.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return Content(**data)

        return None

    def list_content(
        self, persona_id: Optional[str] = None, status: str = "draft"
    ) -> List[Content]:
        """List content, optionally filtered by persona_id."""
        contents = []
        folder = "drafts" if status == "draft" else "published"

        if persona_id:
            # Search only in specific persona's directory
            content_dir = self.base_path / "personas" / persona_id / "content" / folder
            if content_dir.exists():
                for file_path in content_dir.glob("*.json"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    contents.append(Content(**data))
        else:
            # Search across all personas
            personas_dir = self.base_path / "personas"
            if personas_dir.exists():
                for persona_dir in personas_dir.iterdir():
                    if not persona_dir.is_dir():
                        continue
                    content_dir = persona_dir / "content" / folder
                    if content_dir.exists():
                        for file_path in content_dir.glob("*.json"):
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            contents.append(Content(**data))

        # Also check legacy location for backwards compatibility
        legacy_dir = self.base_path / "content_library" / folder
        if legacy_dir.exists():
            for file_path in legacy_dir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                content = Content(**data)
                # Filter by persona_id if specified
                if persona_id is None or content.persona_id == persona_id:
                    # Avoid duplicates
                    if not any(c.id == content.id for c in contents):
                        contents.append(content)

        return sorted(contents, key=lambda c: c.created_at, reverse=True)

    def move_to_published(self, content_id: str) -> bool:
        """Move content from draft to published."""
        content = self.load_content(content_id, status="draft")
        if not content:
            return False

        # Save to published (new location under persona)
        self.save_content(content, status="published")

        # Delete from drafts (check both new and legacy locations)
        # New location
        if content.persona_id:
            draft_dir = self._get_content_dir(content.persona_id, "draft")
            for file_path in draft_dir.glob(f"*_{content_id}.json"):
                file_path.unlink()

        # Legacy location
        legacy_dir = self.base_path / "content_library" / "drafts"
        if legacy_dir.exists():
            for file_path in legacy_dir.glob(f"*_{content_id}.json"):
                file_path.unlink()

        return True

    def delete_content(self, content_id: str, status: str = "draft") -> bool:
        """
        Delete content by ID.

        Args:
            content_id: Content ID to delete
            status: Content status ("draft" or "published")

        Returns:
            True if content was deleted, False if not found
        """
        deleted = False

        # Search in persona directories (new structure)
        personas_dir = self.base_path / "personas"
        if personas_dir.exists():
            for persona_dir in personas_dir.iterdir():
                if not persona_dir.is_dir():
                    continue
                folder = "drafts" if status == "draft" else "published"
                content_dir = persona_dir / "content" / folder
                if content_dir.exists():
                    for file_path in content_dir.glob(f"*_{content_id}.json"):
                        file_path.unlink()
                        deleted = True

        # Also check legacy location
        folder = "drafts" if status == "draft" else "published"
        legacy_dir = self.base_path / "content_library" / folder
        if legacy_dir.exists():
            for file_path in legacy_dir.glob(f"*_{content_id}.json"):
                file_path.unlink()
                deleted = True

        return deleted

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

    def load_review_report(self, content_id: str, persona_id: str) -> Optional[ReviewReport]:
        """Load review report"""
        report_path = self.base_path / "personas" / persona_id / "reviews" / f"{content_id}.json"
        if not report_path.exists():
            return None

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ReviewReport(**data)

    # ========================================================================
    # Simulation Reports
    # ========================================================================

    def save_simulation_report(self, report: SimulationReport, persona_id: str) -> None:
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
            self.base_path / "personas" / persona_id / "simulations" / f"{content_id}.json"
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

    def load_retrospective(self, week: str, persona_id: str) -> Optional[WeeklyRetrospective]:
        """Load retrospective by week"""
        retro_path = self.base_path / "personas" / persona_id / "retrospectives" / f"{week}.json"
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
    # Evolution Management
    # ========================================================================

    def _get_evolution_dir(self, persona_id: str) -> Path:
        """Get evolution directory for a persona."""
        evolution_dir = self.base_path / "personas" / persona_id / "evolution"
        evolution_dir.mkdir(parents=True, exist_ok=True)
        return evolution_dir

    def save_evolution_suggestion(self, persona_id: str, suggestion: EvolutionSuggestion) -> None:
        """
        Save an evolution suggestion.

        Args:
            persona_id: Persona ID
            suggestion: EvolutionSuggestion to save
        """
        evolution_dir = self._get_evolution_dir(persona_id)
        suggestions_path = evolution_dir / "suggestions.json"

        # Load existing suggestions
        suggestions = []
        if suggestions_path.exists():
            with open(suggestions_path, "r", encoding="utf-8") as f:
                suggestions = json.load(f)

        # Check if suggestion with same ID exists (update) or add new
        updated = False
        for i, s in enumerate(suggestions):
            if s.get("id") == suggestion.id:
                suggestions[i] = suggestion.model_dump(mode="json")
                updated = True
                break

        if not updated:
            suggestions.append(suggestion.model_dump(mode="json"))

        with open(suggestions_path, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, indent=2, ensure_ascii=False)

    def load_evolution_suggestion(
        self, persona_id: str, suggestion_id: str
    ) -> Optional[EvolutionSuggestion]:
        """
        Load a specific evolution suggestion.

        Args:
            persona_id: Persona ID
            suggestion_id: Suggestion ID

        Returns:
            EvolutionSuggestion or None if not found
        """
        evolution_dir = self._get_evolution_dir(persona_id)
        suggestions_path = evolution_dir / "suggestions.json"

        if not suggestions_path.exists():
            return None

        with open(suggestions_path, "r", encoding="utf-8") as f:
            suggestions = json.load(f)

        for s in suggestions:
            if s.get("id") == suggestion_id:
                return EvolutionSuggestion(**s)

        return None

    def list_evolution_suggestions(
        self,
        persona_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[EvolutionSuggestion]:
        """
        List evolution suggestions for a persona.

        Args:
            persona_id: Persona ID
            status: Filter by status (pending, approved, rejected, auto_applied)
            limit: Maximum number of suggestions to return

        Returns:
            List of EvolutionSuggestion, newest first
        """
        evolution_dir = self._get_evolution_dir(persona_id)
        suggestions_path = evolution_dir / "suggestions.json"

        if not suggestions_path.exists():
            return []

        with open(suggestions_path, "r", encoding="utf-8") as f:
            suggestions = json.load(f)

        result = []
        for s in suggestions:
            if status is None or s.get("status") == status:
                result.append(EvolutionSuggestion(**s))

        # Sort by created_at descending
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result[:limit]

    def save_feedback_analysis(self, persona_id: str, analysis: EvolutionFeedbackAnalysis) -> None:
        """
        Save feedback analysis results.

        Args:
            persona_id: Persona ID
            analysis: EvolutionFeedbackAnalysis to save
        """
        evolution_dir = self._get_evolution_dir(persona_id)
        analysis_path = evolution_dir / "feedback_analysis.json"

        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_feedback_analysis(self, persona_id: str) -> Optional[EvolutionFeedbackAnalysis]:
        """
        Load latest feedback analysis.

        Args:
            persona_id: Persona ID

        Returns:
            EvolutionFeedbackAnalysis or None if not found
        """
        evolution_dir = self._get_evolution_dir(persona_id)
        analysis_path = evolution_dir / "feedback_analysis.json"

        if not analysis_path.exists():
            return None

        with open(analysis_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return EvolutionFeedbackAnalysis(**data)

    def save_agent_config(self, persona_id: str, agent_type: str, config: AgentConfig) -> None:
        """
        Save per-persona agent configuration.

        This also updates the persona's agent_configs field.

        Args:
            persona_id: Persona ID
            agent_type: Agent type (content, review, discovery)
            config: AgentConfig to save
        """
        # Load persona and update agent_configs
        persona = self.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        # Update agent_configs
        if persona.agent_configs is None:
            persona.agent_configs = {}
        persona.agent_configs[agent_type] = config

        # Save persona
        self.save_persona(persona)

    def load_agent_config(self, persona_id: str, agent_type: str) -> Optional[AgentConfig]:
        """
        Load per-persona agent configuration.

        Args:
            persona_id: Persona ID
            agent_type: Agent type (content, review, discovery)

        Returns:
            AgentConfig or None if not found
        """
        persona = self.load_persona(persona_id)
        if not persona or not persona.agent_configs:
            return None

        config_data = persona.agent_configs.get(agent_type)
        if config_data is None:
            return None

        # If it's already an AgentConfig, return it
        if isinstance(config_data, AgentConfig):
            return config_data

        # Otherwise parse from dict
        return AgentConfig(**config_data)

    def get_persona_version(self, persona_id: str, version: str) -> Optional[Persona]:
        """
        Load a specific version of a persona.

        Args:
            persona_id: Persona ID
            version: Version string (e.g., "v1.0", "v1.5")

        Returns:
            Persona at that version or None if not found
        """
        versions_dir = self.base_path / "personas" / persona_id / "versions"
        version_path = versions_dir / f"{version}.yaml"

        if not version_path.exists():
            return None

        with open(version_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Persona(**data)

    def list_persona_versions(self, persona_id: str) -> List[str]:
        """
        List all available versions of a persona.

        Args:
            persona_id: Persona ID

        Returns:
            List of version strings, newest first
        """
        versions_dir = self.base_path / "personas" / persona_id / "versions"

        if not versions_dir.exists():
            return []

        versions = []
        for version_path in versions_dir.glob("v*.yaml"):
            versions.append(version_path.stem)

        # Sort by version number descending
        def version_key(v: str) -> tuple:
            parts = v.lstrip("v").split(".")
            return tuple(int(p) for p in parts)

        return sorted(versions, key=version_key, reverse=True)

    # ========================================================================
    # Discovery Results (Trending Data)
    # ========================================================================

    def save_discovery_results(
        self,
        persona_id: str,
        platform: str,
        results: Dict[str, Any],
    ) -> str:
        """
        Save discovery/trending results for a persona with timestamp.

        Results are saved as timestamped files for historical tracking.
        Filename format: {datetime}_{platform}.json

        Args:
            persona_id: Persona ID
            platform: Platform name (e.g., "bluesky", "twitter")
            results: Discovery results including patterns and ideas

        Returns:
            Path to saved file
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"
        discovery_dir.mkdir(parents=True, exist_ok=True)

        # Filename with timestamp: 2026-02-06_12-00_bluesky.json
        now = datetime.now()
        datetime_str = now.strftime("%Y-%m-%d_%H-%M")
        filename = f"{datetime_str}_{platform}.json"
        result_path = discovery_dir / filename

        data = {
            "platform": platform,
            "created_at": now.isoformat(),
            **results,
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(result_path)

    def get_latest_discovery(
        self,
        persona_id: str,
        platform: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest discovery results for a persona.

        Finds the most recent discovery file by timestamp.

        Args:
            persona_id: Persona ID
            platform: Platform name (optional, returns most recent if not specified)

        Returns:
            Discovery results or None if not found
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"

        if not discovery_dir.exists():
            return None

        # Find files matching pattern
        if platform:
            pattern = f"*_{platform}.json"
        else:
            pattern = "*.json"

        # Get all matching files sorted by name (timestamp) descending
        files = sorted(discovery_dir.glob(pattern), reverse=True)

        if not files:
            # Fallback: check legacy format (platform.json without timestamp)
            if platform:
                legacy_path = discovery_dir / f"{platform}.json"
                if legacy_path.exists():
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        return json.load(f)
            return None

        # Return most recent file
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def list_discovery_history(
        self,
        persona_id: str,
        platform: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List discovery history for a persona.

        Args:
            persona_id: Persona ID
            platform: Platform name (optional, filter by platform)
            limit: Maximum number of results to return

        Returns:
            List of discovery results, newest first
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"

        if not discovery_dir.exists():
            return []

        # Find files matching pattern
        if platform:
            pattern = f"*_{platform}.json"
        else:
            pattern = "*.json"

        # Get all matching files sorted by name (timestamp) descending
        files = sorted(discovery_dir.glob(pattern), reverse=True)[:limit]

        results = []
        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_filename"] = file_path.name
            results.append(data)

        return results

    def list_discovery_platforms(self, persona_id: str) -> List[str]:
        """
        List platforms with discovery results for a persona.

        Args:
            persona_id: Persona ID

        Returns:
            List of unique platform names
        """
        persona_dir = self.base_path / "personas" / persona_id
        discovery_dir = persona_dir / "discovery"

        if not discovery_dir.exists():
            return []

        # Extract platform names from filenames
        # Format: {datetime}_{platform}.json or {platform}.json (legacy)
        platforms = set()
        for file_path in discovery_dir.glob("*.json"):
            name = file_path.stem  # Remove .json
            # Check if it's new format with timestamp
            parts = name.split("_")
            if len(parts) >= 3:
                # New format: 2026-02-06_12-00_bluesky -> bluesky
                platform = "_".join(parts[2:])
            else:
                # Legacy format: bluesky
                platform = name
            platforms.add(platform)

        return list(platforms)

    # ========================================================================
    # Recommended Personas
    # ========================================================================

    def _get_recommendations_dir(self, subdir: str = "personas") -> Path:
        """Get recommendations directory."""
        rec_dir = self.base_path / "recommendations" / subdir
        rec_dir.mkdir(parents=True, exist_ok=True)
        return rec_dir

    def save_recommended_personas(
        self,
        personas: List[RecommendedPersona],
        date: Optional[str] = None,
    ) -> str:
        """
        Save recommended personas with date-based filename.

        Args:
            personas: List of RecommendedPersona to save
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Path to saved file
        """
        rec_dir = self._get_recommendations_dir("personas")

        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        filename = f"{date}.json"
        file_path = rec_dir / filename

        data = [p.model_dump(mode="json") for p in personas]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def get_recommended_personas(
        self,
        limit: int = 10,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[RecommendedPersona]:
        """
        Get recommended personas, optionally filtered.

        Searches recent files and returns matching recommendations.

        Args:
            limit: Maximum number of recommendations to return
            domain: Filter by domain (e.g., "tech", "lifestyle")
            status: Filter by status (active, adopted, archived)

        Returns:
            List of RecommendedPersona, newest first
        """
        rec_dir = self._get_recommendations_dir("personas")

        # Get all JSON files sorted by name (date) descending
        files = sorted(rec_dir.glob("*.json"), reverse=True)

        results = []
        for file_path in files:
            if len(results) >= limit:
                break

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                if len(results) >= limit:
                    break

                rec = RecommendedPersona(**item)

                # Apply filters
                if domain and rec.domain.lower() != domain.lower():
                    continue
                if status and rec.status.value != status:
                    continue

                results.append(rec)

        return results

    def get_latest_recommendations(
        self,
        limit: int = 5,
    ) -> List[RecommendedPersona]:
        """
        Get most recent active recommendations.

        Args:
            limit: Maximum number to return

        Returns:
            List of active RecommendedPersona from most recent batch
        """
        return self.get_recommended_personas(limit=limit, status="active")

    def get_recommendation(self, rec_id: str) -> Optional[RecommendedPersona]:
        """
        Get a specific recommendation by ID.

        Args:
            rec_id: Recommendation ID

        Returns:
            RecommendedPersona or None if not found
        """
        rec_dir = self._get_recommendations_dir("personas")

        # Search all files for the ID
        for file_path in rec_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                if item.get("id") == rec_id:
                    return RecommendedPersona(**item)

        return None

    def mark_recommendation_adopted(
        self,
        rec_id: str,
        persona_id: str,
    ) -> bool:
        """
        Mark a recommendation as adopted and link to created persona.

        Args:
            rec_id: Recommendation ID
            persona_id: Created persona ID

        Returns:
            True if updated successfully
        """
        rec_dir = self._get_recommendations_dir("personas")

        # Find and update the recommendation
        for file_path in rec_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            updated = False
            for i, item in enumerate(data):
                if item.get("id") == rec_id:
                    data[i]["status"] = "adopted"
                    data[i]["adopted_persona_id"] = persona_id
                    updated = True
                    break

            if updated:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True

        return False

    # ========================================================================
    # Trend Snapshots
    # ========================================================================

    def save_trend_snapshot(self, snapshot: TrendSnapshot) -> str:
        """
        Save a trend snapshot.

        Args:
            snapshot: TrendSnapshot to save

        Returns:
            Path to saved file
        """
        trend_dir = self._get_recommendations_dir("trends")

        # Filename: {date}_{platform}.json
        date_str = snapshot.captured_at.strftime("%Y-%m-%d")
        filename = f"{date_str}_{snapshot.platform}.json"
        file_path = trend_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

        return str(file_path)

    def get_latest_trend_snapshots(
        self,
        platform: Optional[str] = None,
        limit: int = 5,
    ) -> List[TrendSnapshot]:
        """
        Get latest trend snapshots.

        Args:
            platform: Filter by platform (optional)
            limit: Maximum number to return

        Returns:
            List of TrendSnapshot, newest first
        """
        trend_dir = self._get_recommendations_dir("trends")

        if platform:
            pattern = f"*_{platform}.json"
        else:
            pattern = "*.json"

        files = sorted(trend_dir.glob(pattern), reverse=True)[:limit]

        results = []
        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append(TrendSnapshot(**data))

        return results

    def get_today_trend_snapshots(self) -> List[TrendSnapshot]:
        """
        Get all trend snapshots from today.

        Returns:
            List of TrendSnapshot from today
        """
        trend_dir = self._get_recommendations_dir("trends")
        today = datetime.now().strftime("%Y-%m-%d")
        pattern = f"{today}_*.json"

        results = []
        for file_path in trend_dir.glob(pattern):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append(TrendSnapshot(**data))

        return results

    # ========================================================================
    # Batch Loading Methods (Performance Optimization)
    # ========================================================================

    def list_personas_summary(self) -> List[Dict[str, Any]]:
        """
        Batch load all persona summaries in a single directory traversal.

        Returns minimal data needed for listings, avoiding full persona parsing.

        Returns:
            List of persona summary dicts with id, name, tagline, platforms, created_at
        """
        personas_dir = self.base_path / "personas"
        if not personas_dir.exists():
            return []

        summaries = []
        for persona_dir in personas_dir.iterdir():
            if not persona_dir.is_dir():
                continue

            config_path = persona_dir / "config.yaml"
            if not config_path.exists():
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                identity = data.get("identity", {})
                summaries.append(
                    {
                        "id": data.get("id", persona_dir.name),
                        "name": identity.get("name", "Unknown"),
                        "tagline": identity.get("tagline", ""),
                        "expertise": identity.get("expertise", []),
                        "platforms": data.get("platforms", []),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "version": data.get("version", "v1.0"),
                    }
                )
            except Exception:
                continue

        # Sort by created_at descending
        summaries.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return summaries

    def list_content_with_reviews_batch(
        self,
        persona_id: Optional[str] = None,
        status: str = "draft",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Batch load content with their reviews to avoid N+1 queries.

        Args:
            persona_id: Optional persona ID to filter by
            status: Content status (draft or published)
            limit: Maximum number of items to return

        Returns:
            List of content dicts with embedded review data
        """
        folder = "drafts" if status == "draft" else "published"
        contents = []

        if persona_id:
            persona_ids = [persona_id]
        else:
            personas_dir = self.base_path / "personas"
            if not personas_dir.exists():
                return []
            persona_ids = [d.name for d in personas_dir.iterdir() if d.is_dir()]

        for pid in persona_ids:
            content_dir = self.base_path / "personas" / pid / "content" / folder
            reviews_dir = self.base_path / "personas" / pid / "reviews"

            if not content_dir.exists():
                continue

            # Batch load all reviews for this persona into a dict
            reviews_map: Dict[str, Dict[str, Any]] = {}
            if reviews_dir.exists():
                for review_path in reviews_dir.glob("*.json"):
                    try:
                        content_id = review_path.stem
                        with open(review_path, "r", encoding="utf-8") as f:
                            reviews_map[content_id] = json.load(f)
                    except Exception:
                        continue

            # Load content files
            for file_path in content_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_data = json.load(f)

                    content_id = content_data.get("id", "")
                    review_data = reviews_map.get(content_id)

                    # Embed review summary
                    if review_data:
                        content_data["review"] = {
                            "overall_score": review_data.get("overall_score", 0),
                            "reviewed_at": review_data.get("reviewed_at"),
                            "persona_consistency": review_data.get("persona_consistency", {}).get(
                                "score", 0
                            ),
                            "platform_fit": review_data.get("platform_fit", {}).get("score", 0),
                            "compliance": review_data.get("compliance", {}).get("score", 0),
                            "engagement_potential": review_data.get("engagement_potential", {}).get(
                                "score", 0
                            ),
                        }
                    else:
                        content_data["review"] = None

                    content_data["_status"] = status
                    contents.append(content_data)
                except Exception:
                    continue

        # Sort by created_at descending
        contents.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return contents[:limit]

    def get_batch_persona_stats(
        self,
        persona_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch calculate statistics for multiple personas efficiently.

        Minimizes file I/O by loading data once per persona directory.

        Args:
            persona_ids: List of persona IDs (None = all personas)

        Returns:
            Dict mapping persona_id to stats dict
        """
        if persona_ids is None:
            personas_dir = self.base_path / "personas"
            if not personas_dir.exists():
                return {}
            persona_ids = [d.name for d in personas_dir.iterdir() if d.is_dir()]

        stats: Dict[str, Dict[str, Any]] = {}

        for pid in persona_ids:
            persona_dir = self.base_path / "personas" / pid

            # Count content
            drafts_dir = persona_dir / "content" / "drafts"
            published_dir = persona_dir / "content" / "published"
            reviews_dir = persona_dir / "reviews"

            draft_count = 0
            published_count = 0
            content_by_pillar: Dict[str, int] = {}
            content_by_platform: Dict[str, int] = {}

            # Count drafts and collect metadata
            draft_ids = set()
            if drafts_dir.exists():
                for f in drafts_dir.glob("*.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as fp:
                            data = json.load(fp)
                        draft_ids.add(data.get("id"))
                        draft_count += 1
                        pillar = data.get("pillar", "unknown")
                        platform = data.get("platform", "unknown")
                        content_by_pillar[pillar] = content_by_pillar.get(pillar, 0) + 1
                        content_by_platform[platform] = content_by_platform.get(platform, 0) + 1
                    except Exception:
                        continue

            # Count published (subtract from drafts to avoid double counting)
            published_ids = set()
            if published_dir.exists():
                for f in published_dir.glob("*.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as fp:
                            data = json.load(fp)
                        content_id = data.get("id")
                        published_ids.add(content_id)
                        # Only count if not already counted as draft
                        if content_id not in draft_ids:
                            published_count += 1
                            pillar = data.get("pillar", "unknown")
                            platform = data.get("platform", "unknown")
                            content_by_pillar[pillar] = content_by_pillar.get(pillar, 0) + 1
                            content_by_platform[platform] = content_by_platform.get(platform, 0) + 1
                        else:
                            published_count += 1
                            draft_count -= 1  # Don't count as draft if published
                    except Exception:
                        continue

            # Calculate review scores
            total_consistency = 0
            total_platform_fit = 0
            total_compliance = 0
            total_engagement = 0
            review_count = 0

            if reviews_dir.exists():
                for f in reviews_dir.glob("*.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as fp:
                            review = json.load(fp)
                        total_consistency += review.get("persona_consistency", {}).get("score", 0)
                        total_platform_fit += review.get("platform_fit", {}).get("score", 0)
                        total_compliance += review.get("compliance", {}).get("score", 0)
                        total_engagement += review.get("engagement_potential", {}).get("score", 0)
                        review_count += 1
                    except Exception:
                        continue

            avg_score = 0
            if review_count > 0:
                avg_score = (
                    total_consistency + total_platform_fit + total_compliance + total_engagement
                ) / (review_count * 4)

            stats[pid] = {
                "persona_id": pid,
                "total_content": draft_count + published_count,
                "published_content": published_count,
                "draft_content": draft_count,
                "avg_review_score": round(avg_score),
                "content_by_pillar": content_by_pillar,
                "content_by_platform": content_by_platform,
                "score_distribution": {
                    "persona_consistency": (
                        round(total_consistency / review_count) if review_count > 0 else 0
                    ),
                    "platform_fit": (
                        round(total_platform_fit / review_count) if review_count > 0 else 0
                    ),
                    "compliance": round(total_compliance / review_count) if review_count > 0 else 0,
                    "engagement_potential": (
                        round(total_engagement / review_count) if review_count > 0 else 0
                    ),
                },
            }

        return stats

    def get_all_reviews_batch(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch load all reviews across personas.

        Args:
            persona_id: Optional persona ID to filter by

        Returns:
            Dict mapping content_id to review data
        """
        if persona_id:
            persona_ids = [persona_id]
        else:
            personas_dir = self.base_path / "personas"
            if not personas_dir.exists():
                return {}
            persona_ids = [d.name for d in personas_dir.iterdir() if d.is_dir()]

        reviews: Dict[str, Dict[str, Any]] = {}

        for pid in persona_ids:
            reviews_dir = self.base_path / "personas" / pid / "reviews"
            if not reviews_dir.exists():
                continue

            for review_path in reviews_dir.glob("*.json"):
                try:
                    content_id = review_path.stem
                    with open(review_path, "r", encoding="utf-8") as f:
                        review_data = json.load(f)
                    review_data["_persona_id"] = pid
                    reviews[content_id] = review_data
                except Exception:
                    continue

        return reviews
