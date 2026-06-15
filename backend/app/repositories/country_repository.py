"""Repository for the Country model."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.repositories.base import BaseRepository


class CountryRepository(BaseRepository[Country]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Country)

    async def get_by_code(self, code: str) -> Optional[Country]:
        query = select(self.model).where(self.model.code == code)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all_ordered(self, skip: int = 0, limit: int = 100) -> list[Country]:
        query = select(self.model).order_by(self.model.name).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        return await self.count()
