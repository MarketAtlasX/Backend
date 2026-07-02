"""Repository for the MilitaryRelation model."""

from typing import List

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.military_relation import MilitaryRelation
from app.repositories.base import BaseRepository


class MilitaryRelationRepository(BaseRepository[MilitaryRelation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MilitaryRelation)

    async def get_by_country(self, code: str) -> List[MilitaryRelation]:
        query = select(self.model).where(
            or_(self.model.country_a == code, self.model.country_b == code)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all(self) -> List[MilitaryRelation]:
        query = select(self.model)
        result = await self.session.execute(query)
        return list(result.scalars().all())
