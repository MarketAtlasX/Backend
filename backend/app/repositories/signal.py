from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.signal import Signal
from app.repositories.base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    """Repository for Signal model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Signal)

    async def get_by_event_id(
        self, 
        event_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Signal]:
        """Get all signals for an event."""
        query = (
            select(self.model)
            .where(self.model.event_id == event_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_entity_id(
        self, 
        entity_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Signal]:
        """Get all signals for an entity."""
        query = (
            select(self.model)
            .where(self.model.entity_id == entity_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_type(
        self, 
        signal_type: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Signal]:
        """Get signals filtered by type (buy, sell, hold, short)."""
        query = (
            select(self.model)
            .where(self.model.signal_type == signal_type)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_status(
        self, 
        status: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Signal]:
        """Get signals filtered by status (active, closed, expired)."""
        query = (
            select(self.model)
            .where(self.model.status == status)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_high_confidence(
        self, 
        min_confidence: float = 0.75, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Signal]:
        """Get signals with confidence above threshold."""
        query = (
            select(self.model)
            .where(self.model.confidence >= min_confidence)
            .order_by(desc(self.model.confidence))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Signal]:
        """Get all active signals (convenient shortcut)."""
        return await self.get_by_status("active", skip, limit)

    async def get_by_event_and_entity(
        self, 
        event_id: int, 
        entity_id: int
    ) -> Optional[Signal]:
        """Get signal for a specific event-entity combination."""
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.event_id == event_id,
                    self.model.entity_id == entity_id,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_with_relationships(self, signal_id: int) -> Optional[Signal]:
        """Get signal with event and entity eagerly loaded."""
        query = (
            select(self.model)
            .where(self.model.id == signal_id)
            .options(
                selectinload(self.model.event),
                selectinload(self.model.entity),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()
