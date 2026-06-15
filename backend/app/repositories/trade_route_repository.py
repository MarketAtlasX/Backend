"""Repository for the TradeRoute model."""

from typing import List

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_route import TradeRoute
from app.repositories.base import BaseRepository


class TradeRouteRepository(BaseRepository[TradeRoute]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TradeRoute)

    async def get_by_country(self, code: str) -> List[TradeRoute]:
        query = select(self.model).where(
            or_(self.model.from_country == code, self.model.to_country == code)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all(self) -> List[TradeRoute]:
        query = select(self.model)
        result = await self.session.execute(query)
        return list(result.scalars().all())
