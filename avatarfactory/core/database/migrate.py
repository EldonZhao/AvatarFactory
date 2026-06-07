"""
Migration script to convert file-based storage to database.

Usage:
    python -m avatarfactory.core.database.migrate

Or via CLI:
    avatarfactory migrate-db [--kb-path ./knowledges] [--db-url sqlite:///...]
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from avatarfactory.core.database.connection import get_session, init_database, reset_engine
from avatarfactory.core.database.models import (
    PersonaModel,
    PersonaVersionModel,
    ContentModel,
    ReviewModel,
    DiscoveryResultModel,
    ScheduledTaskModel,
    TrendSnapshotModel,
    RecommendedPersonaModel,
)

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    """Report of migration results."""

    personas_migrated: int = 0
    personas_errors: int = 0
    persona_versions_migrated: int = 0
    contents_migrated: int = 0
    contents_errors: int = 0
    reviews_migrated: int = 0
    discoveries_migrated: int = 0
    discoveries_errors: int = 0
    evolution_suggestions_migrated: int = 0
    tasks_migrated: int = 0
    tasks_errors: int = 0
    trends_migrated: int = 0
    trends_errors: int = 0
    recommendations_migrated: int = 0
    recommendations_errors: int = 0
    error_details: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a summary string."""
        lines = [
            "Migration Report",
            "=" * 40,
            f"Personas:              {self.personas_migrated} (errors: {self.personas_errors})",
            f"Persona Versions:      {self.persona_versions_migrated}",
            f"Contents:              {self.contents_migrated} (errors: {self.contents_errors})",
            f"Reviews:               {self.reviews_migrated}",
            f"Discoveries:           {self.discoveries_migrated} (errors: {self.discoveries_errors})",
            f"Scheduled Tasks:       {self.tasks_migrated} (errors: {self.tasks_errors})",
            f"Trend Snapshots:       {self.trends_migrated} (errors: {self.trends_errors})",
            f"Recommendations:       {self.recommendations_migrated} (errors: {self.recommendations_errors})",
            "=" * 40,
        ]
        total_errors = (
            self.personas_errors
            + self.contents_errors
            + self.discoveries_errors
            + self.tasks_errors
            + self.trends_errors
            + self.recommendations_errors
        )
        if total_errors > 0:
            lines.append(f"Total Errors: {total_errors}")
            for err in self.error_details[:10]:
                lines.append(f"  - {err}")
            if len(self.error_details) > 10:
                lines.append(f"  ... and {len(self.error_details) - 10} more")
        else:
            lines.append("No errors!")
        return "\n".join(lines)


def load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load YAML {path}: {e}")
        return None


def load_json_file(path: Path) -> Optional[Any]:
    """Load a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load JSON {path}: {e}")
        return None


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


async def migrate_personas(kb_path: Path, report: MigrationReport) -> Dict[str, PersonaModel]:
    """Migrate all personas from file system to database."""
    personas_dir = kb_path / "personas"
    if not personas_dir.exists():
        return {}

    personas: Dict[str, PersonaModel] = {}

    async with get_session() as session:
        for persona_dir in personas_dir.iterdir():
            if not persona_dir.is_dir():
                continue

            persona_id = persona_dir.name
            config_path = persona_dir / "config.yaml"

            if not config_path.exists():
                continue

            try:
                config = load_yaml_file(config_path)
                if not config:
                    continue

                identity = config.get("identity", {})
                persona = PersonaModel(
                    id=persona_id,
                    version=config.get("version", "v1.0"),
                    name=identity.get("name", persona_id),
                    tagline=identity.get("tagline"),
                    expertise=identity.get("expertise"),
                    identity=identity,
                    target_audience=config.get("target_audience", {}),
                    voice_style=config.get("voice_style", {}),
                    content_pillars=config.get("content_pillars", {}),
                    boundaries=config.get("boundaries", {}),
                    notification=config.get("notification"),
                    evolution=config.get("evolution"),
                    agent_configs=config.get("agent_configs"),
                    metadata_=config.get("metadata"),
                )
                session.add(persona)
                personas[persona_id] = persona
                report.personas_migrated += 1

                # Migrate version history
                history_path = persona_dir / "history.json"
                if history_path.exists():
                    history = load_json_file(history_path) or []
                    for entry in history:
                        version = PersonaVersionModel(
                            persona_id=persona_id,
                            version=entry.get("version", "v1.0"),
                            timestamp=parse_datetime(entry.get("timestamp")) or datetime.utcnow(),
                            changes=entry.get("changes", []),
                            reason=entry.get("reason", ""),
                            expected_impact=entry.get("expected_impact", ""),
                            author=entry.get("author", "user"),
                            approved=entry.get("approved", False),
                            config_snapshot=entry.get("config_snapshot", config),
                        )
                        session.add(version)
                        report.persona_versions_migrated += 1

            except Exception as e:
                report.personas_errors += 1
                report.error_details.append(f"Persona {persona_id}: {e}")
                logger.error(f"Failed to migrate persona {persona_id}: {e}")

        await session.commit()

    return personas


async def migrate_contents(kb_path: Path, report: MigrationReport) -> None:
    """Migrate all contents from file system to database."""
    personas_dir = kb_path / "personas"
    if not personas_dir.exists():
        return

    # First pass: collect all contents, preferring published over draft
    contents_to_migrate: Dict[str, Dict[str, Any]] = {}
    content_files: Dict[str, Path] = {}

    for persona_dir in personas_dir.iterdir():
        if not persona_dir.is_dir():
            continue

        persona_id = persona_dir.name
        content_dir = persona_dir / "content"

        if not content_dir.exists():
            continue

        # Process drafts first, then published (so published overwrites drafts)
        for status_dir in ["drafts", "published"]:
            status_path = content_dir / status_dir
            if not status_path.exists():
                continue

            status = "draft" if status_dir == "drafts" else "published"

            for content_file in status_path.glob("*.json"):
                try:
                    data = load_json_file(content_file)
                    if not data:
                        continue

                    content_id = data.get("id") or content_file.stem.split("_")[-1]

                    # If already exists and current is published, overwrite
                    # If already exists and current is draft, skip
                    if content_id in contents_to_migrate:
                        if status == "draft":
                            continue  # Don't overwrite published with draft

                    contents_to_migrate[content_id] = {
                        "persona_id": persona_id,
                        "persona_dir": persona_dir,
                        "data": data,
                        "status": status,
                    }
                    content_files[content_id] = content_file

                except Exception as e:
                    report.contents_errors += 1
                    report.error_details.append(f"Content {content_file}: {e}")
                    logger.error(f"Failed to load content {content_file}: {e}")

    # Second pass: insert into database
    async with get_session() as session:
        for content_id, content_info in contents_to_migrate.items():
            try:
                persona_id = content_info["persona_id"]
                persona_dir = content_info["persona_dir"]
                data = content_info["data"]
                status = content_info["status"]

                content = ContentModel(
                    id=content_id,
                    persona_id=persona_id,
                    created_at=parse_datetime(data.get("created_at")) or datetime.utcnow(),
                    title=data.get("title", ""),
                    body=data.get("body", ""),
                    pillar=data.get("pillar", ""),
                    platform=data.get("platform", "unknown"),
                    content_type=data.get("content_type", "text"),
                    status=status,
                    published_at=parse_datetime(data.get("published_at")),
                    structure=data.get("structure"),
                    tags=data.get("tags"),
                    media=data.get("media"),
                    image_prompts=data.get("image_prompts"),
                    review_score=data.get("review_score"),
                    predicted_engagement=data.get("predicted_engagement"),
                    metadata_=data.get("metadata"),
                )
                session.add(content)
                report.contents_migrated += 1

                # Migrate review if exists
                reviews_dir = persona_dir / "reviews"
                review_file = reviews_dir / f"{content_id}.json"
                if review_file.exists():
                    review_data = load_json_file(review_file)
                    if review_data:
                        review = ReviewModel(
                            content_id=content_id,
                            reviewed_at=parse_datetime(review_data.get("reviewed_at"))
                            or datetime.utcnow(),
                            persona_consistency_score=review_data.get(
                                "persona_consistency", {}
                            ).get("score", 0),
                            platform_fit_score=review_data.get("platform_fit", {}).get("score", 0),
                            compliance_score=review_data.get("compliance", {}).get("score", 0),
                            engagement_potential_score=review_data.get(
                                "engagement_potential", {}
                            ).get("score", 0),
                            overall_score=review_data.get("overall_score", 0),
                            persona_consistency=review_data.get("persona_consistency", {}),
                            platform_fit=review_data.get("platform_fit", {}),
                            compliance=review_data.get("compliance", {}),
                            engagement_potential=review_data.get("engagement_potential", {}),
                            suggestions=review_data.get("suggestions"),
                        )
                        session.add(review)
                        report.reviews_migrated += 1

                        # Update denormalized score
                        content.review_score = review.overall_score

            except Exception as e:
                report.contents_errors += 1
                report.error_details.append(f"Content {content_id}: {e}")
                logger.error(f"Failed to migrate content {content_id}: {e}")

        await session.commit()


async def migrate_discoveries(kb_path: Path, report: MigrationReport) -> None:
    """Migrate discovery results from file system to database."""
    personas_dir = kb_path / "personas"
    if not personas_dir.exists():
        return

    async with get_session() as session:
        for persona_dir in personas_dir.iterdir():
            if not persona_dir.is_dir():
                continue

            persona_id = persona_dir.name
            discovery_dir = persona_dir / "discovery"

            if not discovery_dir.exists():
                continue

            for discovery_file in discovery_dir.glob("*.json"):
                try:
                    data = load_json_file(discovery_file)
                    if not data:
                        continue

                    # Parse filename for platform and datetime
                    parts = discovery_file.stem.split("_")
                    platform = parts[-1] if parts else "unknown"

                    ideas = data.get("ideas", [])
                    discovery = DiscoveryResultModel(
                        persona_id=persona_id,
                        platform=platform,
                        created_at=parse_datetime(data.get("created_at")) or datetime.utcnow(),
                        trending_count=len(data.get("trending_posts", [])),
                        ideas_count=len(ideas),
                        pattern_analysis=data.get("pattern_analysis"),
                        ideas=ideas,
                        persona_suggestions=data.get("persona_suggestions"),
                        raw_data=data.get("raw_data"),
                    )
                    session.add(discovery)
                    report.discoveries_migrated += 1

                except Exception as e:
                    report.discoveries_errors += 1
                    report.error_details.append(f"Discovery {discovery_file}: {e}")

        await session.commit()


async def migrate_scheduled_tasks(kb_path: Path, report: MigrationReport) -> None:
    """Migrate scheduled tasks from file system to database."""
    tasks_file = kb_path / "scheduler" / "tasks.json"
    if not tasks_file.exists():
        return

    async with get_session() as session:
        tasks = load_json_file(tasks_file) or []

        for task_data in tasks:
            try:
                task = ScheduledTaskModel(
                    id=task_data.get("id"),
                    name=task_data.get("name", ""),
                    task_type=task_data.get("task_type", ""),
                    schedule=task_data.get("schedule", ""),
                    enabled=task_data.get("enabled", True),
                    persona_id=task_data.get("persona_id"),
                    platform=task_data.get("platform"),
                    extra_params=task_data.get("extra_params"),
                    last_run=parse_datetime(task_data.get("last_run")),
                    last_status=task_data.get("last_status"),
                    last_error=task_data.get("last_error"),
                    run_count=task_data.get("run_count", 0),
                )
                session.add(task)
                report.tasks_migrated += 1

            except Exception as e:
                report.tasks_errors += 1
                report.error_details.append(f"Task {task_data.get('id')}: {e}")

        await session.commit()


async def migrate_trends(kb_path: Path, report: MigrationReport) -> None:
    """Migrate trend snapshots from file system to database."""
    trends_dir = kb_path / "recommendations" / "trends"
    if not trends_dir.exists():
        return

    async with get_session() as session:
        for trend_file in trends_dir.glob("*.json"):
            try:
                data = load_json_file(trend_file)
                if not data:
                    continue

                # Parse filename for date and platform
                parts = trend_file.stem.split("_")
                platform = parts[-1] if len(parts) > 1 else "unknown"

                snapshot = TrendSnapshotModel(
                    id=trend_file.stem,
                    platform=platform,
                    captured_at=parse_datetime(data.get("captured_at")) or datetime.utcnow(),
                    trending_topics=data.get("trending_topics"),
                    trending_hashtags=data.get("trending_hashtags"),
                    top_posts=data.get("top_posts"),
                    analysis_summary=data.get("analysis_summary"),
                    key_themes=data.get("key_themes"),
                    content_patterns=data.get("content_patterns"),
                )
                session.add(snapshot)
                report.trends_migrated += 1

            except Exception as e:
                report.trends_errors += 1
                report.error_details.append(f"Trend {trend_file}: {e}")

        await session.commit()


async def migrate_recommendations(kb_path: Path, report: MigrationReport) -> None:
    """Migrate persona recommendations from file system to database."""
    recs_dir = kb_path / "recommendations" / "personas"
    if not recs_dir.exists():
        return

    async with get_session() as session:
        for rec_file in recs_dir.glob("*.json"):
            try:
                data = load_json_file(rec_file)
                if not data:
                    continue

                # Handle both single recommendation and list formats
                recs_list = data if isinstance(data, list) else data.get("recommendations", [data])

                for rec_data in recs_list:
                    if not rec_data.get("name"):
                        continue

                    rec = RecommendedPersonaModel(
                        id=rec_data.get(
                            "id", f"rec_{rec_file.stem}_{hash(rec_data.get('name', ''))}"
                        ),
                        created_at=parse_datetime(rec_data.get("created_at")) or datetime.utcnow(),
                        source_platforms=rec_data.get("source_platforms"),
                        source_trends=rec_data.get("source_trends"),
                        name=rec_data.get("name", ""),
                        tagline=rec_data.get("tagline"),
                        domain=rec_data.get("domain", "general"),
                        expertise=rec_data.get("expertise"),
                        target_audience=rec_data.get("target_audience"),
                        audience_pain_points=rec_data.get("audience_pain_points"),
                        suggested_tone=rec_data.get("suggested_tone"),
                        content_types=rec_data.get("content_types"),
                        content_pillars=rec_data.get("content_pillars"),
                        relevance_score=rec_data.get("relevance_score"),
                        potential_score=rec_data.get("potential_score"),
                        rationale=rec_data.get("rationale"),
                        status=rec_data.get("status", "active"),
                    )
                    session.add(rec)
                    report.recommendations_migrated += 1

            except Exception as e:
                report.recommendations_errors += 1
                report.error_details.append(f"Recommendation {rec_file}: {e}")

        await session.commit()


async def migrate_file_to_db(
    kb_path: str = "./knowledges",
    db_url: Optional[str] = None,
    drop_existing: bool = False,
) -> MigrationReport:
    """
    Migrate all data from file system to database.

    Args:
        kb_path: Path to knowledges directory
        db_url: Optional database URL (defaults to SQLite in kb_path)
        drop_existing: If True, drop existing tables first

    Returns:
        MigrationReport with results
    """
    kb_path = Path(kb_path)
    report = MigrationReport()

    logger.info(f"Starting migration from {kb_path}")

    # Reset engine to ensure fresh connection
    reset_engine()

    # Initialize database
    await init_database(db_url, str(kb_path), drop_existing=drop_existing)

    # Run migrations in order
    logger.info("Migrating personas...")
    await migrate_personas(kb_path, report)

    logger.info("Migrating contents...")
    await migrate_contents(kb_path, report)

    logger.info("Migrating discoveries...")
    await migrate_discoveries(kb_path, report)

    logger.info("Migrating scheduled tasks...")
    await migrate_scheduled_tasks(kb_path, report)

    logger.info("Migrating trends...")
    await migrate_trends(kb_path, report)

    logger.info("Migrating recommendations...")
    await migrate_recommendations(kb_path, report)

    logger.info("Migration complete!")
    return report


def run_migration(
    kb_path: str = "./knowledges",
    db_url: Optional[str] = None,
    drop_existing: bool = False,
) -> MigrationReport:
    """
    Synchronous wrapper for migration.

    Args:
        kb_path: Path to knowledges directory
        db_url: Optional database URL
        drop_existing: If True, drop existing tables first

    Returns:
        MigrationReport with results
    """
    return asyncio.run(migrate_file_to_db(kb_path, db_url, drop_existing))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    kb_path = sys.argv[1] if len(sys.argv) > 1 else "./knowledges"
    report = run_migration(kb_path, drop_existing=True)
    print(report.summary())
