from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_price import MarketPrice
from app.repositories.base import BaseRepository


class MarketPriceRepository(BaseRepository[MarketPrice]):
    """Repository for MarketPrice model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, MarketPrice)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_entity_id(
        self,
        entity_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[MarketPrice]:
        """Get all market prices for an entity."""
        query = (
            select(self.model)
            .where(self.model.entity_id == entity_id)
            .order_by(desc(self.model.price_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_by_entity(self, entity_id: int) -> Optional[MarketPrice]:
        """Get the most recent price for an entity."""
        query = (
            select(self.model)
            .where(self.model.entity_id == entity_id)
            .order_by(desc(self.model.price_date))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_date_range(
        self,
        entity_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[MarketPrice]:
        """Get market prices for an entity within a date range."""
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.entity_id == entity_id,
                    self.model.price_date >= start_date,
                    self.model.price_date <= end_date,
                )
            )
            .order_by(self.model.price_date)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_entity_and_date(
        self,
        entity_id: int,
        price_date: datetime,
    ) -> Optional[MarketPrice]:
        """Get a specific market price record by entity and date (unique constraint)."""
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.entity_id == entity_id,
                    self.model.price_date == price_date,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_recent_by_entity(
        self,
        entity_id: int,
        days: int = 30,
    ) -> List[MarketPrice]:
        """Get market prices for an entity from the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.entity_id == entity_id,
                    self.model.price_date >= cutoff_date,
                )
            )
            .order_by(self.model.price_date)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def exists(self, entity_id: int, price_date: datetime) -> bool:
        """Check if a price record exists (prevents duplicates)."""
        price = await self.get_by_entity_and_date(entity_id, price_date)
        return price is not None

    # ------------------------------------------------------------------
    # Filtered counts
    # ------------------------------------------------------------------

    async def count_by_entity(self, entity_id: int) -> int:
        """Count all price records for a specific entity."""
        return await self.count_where(self.model.entity_id == entity_id)

    async def count_recent_by_entity(self, entity_id: int, days: int = 30) -> int:
        """Count price records for an entity within the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        from sqlalchemy import and_
        return await self.count_where(
            and_(
                self.model.entity_id == entity_id,
                self.model.price_date >= cutoff_date,
            )
        )
