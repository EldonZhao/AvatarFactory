"""
Content repository for database operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from avatarfactory.core.database.models import (
    ContentModel,
    ReviewModel,
    PersonaModel,
)
from avatarfactory.core.database.repositories.base import BaseRepository


class ContentRepository(BaseRepository[ContentModel]):
    """Repository for Content CRUD and queries."""

    model = ContentModel

    async def get_with_review(self, id: str) -> Optional[ContentModel]:
        """
        Get content with review loaded.

        Args:
            id: Content ID

        Returns:
            ContentModel with review or None
        """
        query = (
            select(ContentModel)
            .options(
                selectinload(ContentModel.review),
                selectinload(ContentModel.simulation),
            )
            .where(ContentModel.id == id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_persona(
        self,
        persona_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContentModel]:
        """
        List contents for a specific persona.

        Args:
            persona_id: Persona ID
            status: Optional status filter ('draft', 'published')
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of ContentModel instances
        """
        query = (
            select(ContentModel)
            .where(ContentModel.persona_id == persona_id)
            .order_by(ContentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if status:
            query = query.where(ContentModel.status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_with_reviews(
        self,
        persona_id: Optional[str] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContentModel]:
        """
        List contents with reviews eagerly loaded.

        Args:
            persona_id: Optional persona filter
            status: Optional status filter
            platform: Optional platform filter
            min_score: Minimum review score
            max_score: Maximum review score
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of ContentModel instances with reviews loaded
        """
        query = (
            select(ContentModel)
            .options(selectinload(ContentModel.review))
            .order_by(ContentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        conditions = []
        if persona_id:
            conditions.append(ContentModel.persona_id == persona_id)
        if status:
            conditions.append(ContentModel.status == status)
        if platform:
            conditions.append(ContentModel.platform == platform)
        if min_score is not None:
            conditions.append(ContentModel.review_score >= min_score)
        if max_score is not None:
            conditions.append(ContentModel.review_score <= max_score)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_with_persona_name(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Tuple[ContentModel, str]]:
        """
        List contents with persona names.

        Args:
            status: Optional status filter
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of tuples (ContentModel, persona_name)
        """
        query = (
            select(ContentModel, PersonaModel.name)
            .join(PersonaModel, ContentModel.persona_id == PersonaModel.id)
            .options(selectinload(ContentModel.review))
            .order_by(ContentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if status:
            query = query.where(ContentModel.status == status)

        result = await self.session.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def search(
        self,
        query_text: Optional[str] = None,
        persona_id: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_score: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContentModel]:
        """
        Search contents with multiple criteria.

        Args:
            query_text: Text to search in title and body
            persona_id: Optional persona filter
            platform: Optional platform filter
            status: Optional status filter
            date_from: Start date filter
            date_to: End date filter
            min_score: Minimum review score
            tags: Tags to match (any)
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of matching ContentModel instances
        """
        query = (
            select(ContentModel)
            .options(selectinload(ContentModel.review))
            .order_by(ContentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        conditions = []

        if query_text:
            # SQLite LIKE search (case insensitive)
            search_pattern = f"%{query_text}%"
            conditions.append(
                or_(
                    ContentModel.title.ilike(search_pattern),
                    ContentModel.body.ilike(search_pattern),
                )
            )

        if persona_id:
            conditions.append(ContentModel.persona_id == persona_id)
        if platform:
            conditions.append(ContentModel.platform == platform)
        if status:
            conditions.append(ContentModel.status == status)
        if date_from:
            conditions.append(ContentModel.created_at >= date_from)
        if date_to:
            conditions.append(ContentModel.created_at <= date_to)
        if min_score is not None:
            conditions.append(ContentModel.review_score >= min_score)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get content statistics.

        Args:
            persona_id: Optional persona filter

        Returns:
            Dictionary with counts and averages
        """
        base_condition = ContentModel.persona_id == persona_id if persona_id else True

        # Count by status
        status_counts = await self.session.execute(
            select(
                ContentModel.status,
                func.count().label("count"),
            )
            .where(base_condition)
            .group_by(ContentModel.status)
        )

        # Count by platform
        platform_counts = await self.session.execute(
            select(
                ContentModel.platform,
                func.count().label("count"),
            )
            .where(base_condition)
            .group_by(ContentModel.platform)
        )

        # Average review score
        avg_score = await self.session.execute(
            select(func.avg(ContentModel.review_score))
            .where(base_condition)
            .where(ContentModel.review_score.isnot(None))
        )

        return {
            "by_status": {row[0]: row[1] for row in status_counts},
            "by_platform": {row[0]: row[1] for row in platform_counts},
            "average_score": avg_score.scalar(),
        }

    async def update_review_score(
        self,
        content_id: str,
        score: float,
        issues: Optional[List[str]] = None,
    ) -> bool:
        """
        Update the denormalized review score on content.

        Args:
            content_id: Content ID
            score: Review score
            issues: List of review issues

        Returns:
            True if updated, False if content not found
        """
        content = await self.get(content_id)
        if content:
            content.review_score = score
            content.review_issues = issues
            await self.session.flush()
            return True
        return False

    async def publish(self, content_id: str) -> bool:
        """
        Mark content as published.

        Args:
            content_id: Content ID

        Returns:
            True if published, False if not found
        """
        content = await self.get(content_id)
        if content:
            content.status = "published"
            content.published_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False


class ReviewRepository(BaseRepository[ReviewModel]):
    """Repository for Review CRUD and queries."""

    model = ReviewModel

    async def get_by_content(self, content_id: str) -> Optional[ReviewModel]:
        """
        Get review by content ID.

        Args:
            content_id: Content ID

        Returns:
            ReviewModel or None
        """
        query = select(ReviewModel).where(ReviewModel.content_id == content_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_score_distribution(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Get distribution of review scores.

        Args:
            persona_id: Optional persona filter

        Returns:
            Dictionary mapping score ranges to counts
        """
        query = select(
            func.count().filter(ReviewModel.overall_score >= 80).label("high"),
            func.count().filter(
                and_(ReviewModel.overall_score >= 60, ReviewModel.overall_score < 80)
            ).label("medium"),
            func.count().filter(ReviewModel.overall_score < 60).label("low"),
        )

        if persona_id:
            query = query.join(ContentModel).where(ContentModel.persona_id == persona_id)

        result = await self.session.execute(query)
        row = result.one()
        return {
            "high": row[0] or 0,
            "medium": row[1] or 0,
            "low": row[2] or 0,
        }

    async def get_dimension_averages(
        self,
        persona_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Get average scores for each dimension.

        Args:
            persona_id: Optional persona filter

        Returns:
            Dictionary mapping dimension to average score
        """
        query = select(
            func.avg(ReviewModel.persona_consistency_score).label("persona_consistency"),
            func.avg(ReviewModel.platform_fit_score).label("platform_fit"),
            func.avg(ReviewModel.compliance_score).label("compliance"),
            func.avg(ReviewModel.engagement_potential_score).label("engagement_potential"),
            func.avg(ReviewModel.overall_score).label("overall"),
        )

        if persona_id:
            query = query.join(ContentModel).where(ContentModel.persona_id == persona_id)

        result = await self.session.execute(query)
        row = result.one()
        return {
            "persona_consistency": row[0] or 0,
            "platform_fit": row[1] or 0,
            "compliance": row[2] or 0,
            "engagement_potential": row[3] or 0,
            "overall": row[4] or 0,
        }
