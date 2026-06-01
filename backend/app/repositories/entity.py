from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entity import Entity
from app.repositories.base import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    """Repository for Entity model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Entity)

    async def get_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name (unique field)."""
        query = select(self.model).where(self.model.name == name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_type(
        self, 
        entity_type: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Entity]:
        """Get entities filtered by type (country, company, person, region)."""
        query = (
            select(self.model)
            .where(self.model.entity_type == entity_type)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_country_code(
        self, 
        country_code: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Entity]:
        """Get entities filtered by country code (ISO 3166-1 alpha-2)."""
        query = (
            select(self.model)
            .where(self.model.country_code == country_code)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_ticker(self, ticker: str) -> Optional[Entity]:
        """Get entity by ticker symbol (searches within comma-separated list)."""
        query = (
            select(self.model)
            .where(self.model.ticker_symbols.contains(ticker))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_with_events(self, entity_id: int) -> Optional[Entity]:
        """Get entity with all related events eagerly loaded."""
        query = (
            select(self.model)
            .where(self.model.id == entity_id)
            .options(selectinload(self.model.events))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_with_signals(self, entity_id: int) -> Optional[Entity]:
        """Get entity with all related signals eagerly loaded."""
        query = (
            select(self.model)
            .where(self.model.id == entity_id)
            .options(selectinload(self.model.signals))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_companies(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Entity]:
        """Get all company entities."""
        return await self.get_by_type("company", skip, limit)

    async def get_countries(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Entity]:
        """Get all country entities."""
        return await self.get_by_type("country", skip, limit)
