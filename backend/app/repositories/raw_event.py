from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_event import RawEvent
from app.repositories.base import BaseRepository


class RawEventRepository(BaseRepository[RawEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, RawEvent)

    async def get_unprocessed(self, limit: int = 50) -> list[RawEvent]:
        stmt = select(RawEvent).where(not RawEvent.processed).order_by(RawEvent.fetched_at).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_url(self, url: str) -> bool:
        stmt = select(RawEvent).where(RawEvent.source_url == url)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def mark_processed(self, event_id: int) -> None:
        stmt = select(RawEvent).where(RawEvent.id == event_id)
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if event:
            event.processed = True
            event.processed_at = func.now()
            await self.session.commit()

    async def count_by_source(self) -> list[tuple[str, int]]:
        stmt = select(RawEvent.source, func.count(RawEvent.id)).group_by(RawEvent.source)
        result = await self.session.execute(stmt)
        return list(result.all())
