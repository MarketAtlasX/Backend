from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for Event model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Event)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_id_with_entities(self, event_id: int) -> Optional[Event]:
        """Get event with all related entities eagerly loaded."""
        query = (
            select(self.model)
            .where(self.model.id == event_id)
            .options(selectinload(self.model.entities))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_type(
        self,
        event_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """Get events filtered by type."""
        query = (
            select(self.model)
            .where(self.model.event_type == event_type)
            .order_by(desc(self.model.event_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_severity(
        self,
        severity: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """Get events filtered by severity."""
        query = (
            select(self.model)
            .where(self.model.severity == severity)
            .order_by(desc(self.model.event_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent(
        self,
        days: int = 7,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """Get recent events from the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = (
            select(self.model)
            .where(self.model.event_date >= cutoff_date)
            .order_by(desc(self.model.event_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """Get events filtered by status."""
        query = (
            select(self.model)
            .where(self.model.status == status)
            .order_by(desc(self.model.event_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Filtered counts — mirror the filter predicates above
    # ------------------------------------------------------------------

    async def count_by_type(self, event_type: str) -> int:
        """Count events matching a specific event_type."""
        return await self.count_where(self.model.event_type == event_type)

    async def count_by_severity(self, severity: str) -> int:
        """Count events matching a specific severity."""
        return await self.count_where(self.model.severity == severity)

    async def count_by_status(self, status: str) -> int:
        """Count events matching a specific status."""
        return await self.count_where(self.model.status == status)

    async def count_recent(self, days: int = 7) -> int:
        """Count events within the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return await self.count_where(self.model.event_date >= cutoff_date)
