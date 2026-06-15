"""Repository for the Port model."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.port import Port
from app.repositories.base import BaseRepository


class PortRepository(BaseRepository[Port]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Port)

    async def get_by_country(self, code: str) -> List[Port]:
        query = select(self.model).where(self.model.country_code == code)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all(self) -> List[Port]:
        query = select(self.model)
        result = await self.session.execute(query)
        return list(result.scalars().all())
