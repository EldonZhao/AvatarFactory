"""
Persona repository for database operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from avatarfactory.core.database.models import (
    PersonaModel,
    PersonaVersionModel,
    ContentModel,
    DiscoveryResultModel,
)
from avatarfactory.core.database.repositories.base import BaseRepository
from avatarfactory.models.schemas import Persona


class PersonaRepository(BaseRepository[PersonaModel]):
    """Repository for Persona CRUD and queries."""

    model = PersonaModel

    async def get_with_relations(self, id: str) -> Optional[PersonaModel]:
        """
        Get persona with related data loaded.

        Args:
            id: Persona ID

        Returns:
            PersonaModel with relations or None
        """
        query = (
            select(PersonaModel)
            .options(
                selectinload(PersonaModel.versions),
            )
            .where(PersonaModel.id == id)
            .where(PersonaModel.is_deleted == False)  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PersonaModel]:
        """
        List all active (non-deleted) personas.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of PersonaModel instances
        """
        query = (
            select(PersonaModel)
            .where(PersonaModel.is_deleted == False)  # noqa: E712
            .order_by(PersonaModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def soft_delete(self, id: str) -> bool:
        """
        Soft delete a persona.

        Args:
            id: Persona ID

        Returns:
            True if deleted, False if not found
        """
        persona = await self.get(id)
        if persona:
            persona.is_deleted = True
            persona.updated_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False

    async def get_stats(self, id: str) -> Dict[str, Any]:
        """
        Get statistics for a persona.

        Args:
            id: Persona ID

        Returns:
            Dictionary with content counts, discovery counts, etc.
        """
        # Count contents by status
        draft_count = await self.session.execute(
            select(func.count())
            .select_from(ContentModel)
            .where(ContentModel.persona_id == id)
            .where(ContentModel.status == "draft")
        )
        published_count = await self.session.execute(
            select(func.count())
            .select_from(ContentModel)
            .where(ContentModel.persona_id == id)
            .where(ContentModel.status == "published")
        )

        # Count discoveries
        discovery_count = await self.session.execute(
            select(func.count())
            .select_from(DiscoveryResultModel)
            .where(DiscoveryResultModel.persona_id == id)
        )

        # Sum ideas from discoveries
        ideas_sum = await self.session.execute(
            select(func.sum(DiscoveryResultModel.ideas_count))
            .where(DiscoveryResultModel.persona_id == id)
        )

        return {
            "draft_count": draft_count.scalar() or 0,
            "published_count": published_count.scalar() or 0,
            "discovery_count": discovery_count.scalar() or 0,
            "ideas_count": ideas_sum.scalar() or 0,
        }

    async def get_batch_stats(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for multiple personas in a single query.

        Args:
            ids: List of persona IDs

        Returns:
            Dictionary mapping persona ID to stats
        """
        # Get content counts grouped by persona and status
        content_stats = await self.session.execute(
            select(
                ContentModel.persona_id,
                ContentModel.status,
                func.count().label("count"),
            )
            .where(ContentModel.persona_id.in_(ids))
            .group_by(ContentModel.persona_id, ContentModel.status)
        )

        # Get discovery stats
        discovery_stats = await self.session.execute(
            select(
                DiscoveryResultModel.persona_id,
                func.count().label("discovery_count"),
                func.sum(DiscoveryResultModel.ideas_count).label("ideas_count"),
            )
            .where(DiscoveryResultModel.persona_id.in_(ids))
            .group_by(DiscoveryResultModel.persona_id)
        )

        # Build result dict
        result: Dict[str, Dict[str, Any]] = {
            pid: {
                "draft_count": 0,
                "published_count": 0,
                "discovery_count": 0,
                "ideas_count": 0,
            }
            for pid in ids
        }

        for row in content_stats:
            pid, status, count = row
            if pid in result:
                if status == "draft":
                    result[pid]["draft_count"] = count
                elif status == "published":
                    result[pid]["published_count"] = count

        for row in discovery_stats:
            pid, disc_count, ideas_count = row
            if pid in result:
                result[pid]["discovery_count"] = disc_count or 0
                result[pid]["ideas_count"] = ideas_count or 0

        return result

    # Conversion methods
    def to_schema(self, model: PersonaModel) -> Persona:
        """
        Convert ORM model to Pydantic schema.

        Args:
            model: PersonaModel instance

        Returns:
            Persona schema instance
        """
        return Persona(
            id=model.id,
            version=model.version,
            identity=model.identity,
            target_audience=model.target_audience,
            voice_style=model.voice_style,
            content_pillars=model.content_pillars,
            boundaries=model.boundaries,
            notification=model.notification,
            evolution=model.evolution,
            agent_configs=model.agent_configs or {},
            metadata=model.metadata_ or {},
        )

    def from_schema(self, schema: Persona) -> PersonaModel:
        """
        Convert Pydantic schema to ORM model.

        Args:
            schema: Persona schema instance

        Returns:
            PersonaModel instance
        """
        identity = schema.identity.model_dump() if schema.identity else {}
        return PersonaModel(
            id=schema.id,
            version=schema.version,
            name=identity.get("name", ""),
            tagline=identity.get("tagline"),
            expertise=identity.get("expertise"),
            identity=identity,
            target_audience=schema.target_audience.model_dump() if schema.target_audience else {},
            voice_style=schema.voice_style.model_dump() if schema.voice_style else {},
            content_pillars=schema.content_pillars.model_dump() if schema.content_pillars else {},
            boundaries=schema.boundaries.model_dump() if schema.boundaries else {},
            notification=schema.notification.model_dump() if schema.notification else None,
            evolution=schema.evolution.model_dump() if schema.evolution else None,
            agent_configs=schema.agent_configs,
            metadata_=schema.metadata,
        )

    # Version history methods
    async def save_version(
        self,
        persona_id: str,
        version: str,
        changes: List[str],
        reason: str,
        expected_impact: str,
        config_snapshot: Dict[str, Any],
        author: str = "user",
    ) -> PersonaVersionModel:
        """
        Save a new persona version.

        Args:
            persona_id: Persona ID
            version: Version string (e.g., 'v1.1')
            changes: List of changes made
            reason: Reason for the change
            expected_impact: Expected impact of the change
            config_snapshot: Full configuration at this version
            author: Who made the change

        Returns:
            PersonaVersionModel instance
        """
        version_model = PersonaVersionModel(
            persona_id=persona_id,
            version=version,
            changes=changes,
            reason=reason,
            expected_impact=expected_impact,
            config_snapshot=config_snapshot,
            author=author,
        )
        self.session.add(version_model)
        await self.session.flush()
        return version_model

    async def get_versions(
        self,
        persona_id: str,
        limit: int = 50,
    ) -> List[PersonaVersionModel]:
        """
        Get version history for a persona.

        Args:
            persona_id: Persona ID
            limit: Maximum versions to return

        Returns:
            List of PersonaVersionModel instances (newest first)
        """
        query = (
            select(PersonaVersionModel)
            .where(PersonaVersionModel.persona_id == persona_id)
            .order_by(PersonaVersionModel.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
