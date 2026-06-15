"""Repository for the EventEntity junction table."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_entity import EventEntity
from app.repositories.base import BaseRepository


class EventEntityRepository(BaseRepository[EventEntity]):
    """Repository for managing event-entity associations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, EventEntity)

    async def get_link(
        self, event_id: int, entity_id: int
    ) -> Optional[EventEntity]:
        """Get a specific event-entity link."""
        query = select(self.model).where(
            self.model.event_id == event_id,
            self.model.entity_id == entity_id,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def link_exists(self, event_id: int, entity_id: int) -> bool:
        """Check if a link already exists between an event and entity."""
        return await self.get_link(event_id, entity_id) is not None

    async def create_link(
        self, event_id: int, entity_id: int
    ) -> EventEntity:
        """Create a new link between an event and entity."""
        link = EventEntity(event_id=event_id, entity_id=entity_id)
        self.session.add(link)
        await self.session.flush()
        return link

    async def delete_link(
        self, event_id: int, entity_id: int
    ) -> bool:
        """Delete a link between an event and entity. Returns True if deleted."""
        link = await self.get_link(event_id, entity_id)
        if link is None:
            return False
        await self.session.delete(link)
        await self.session.flush()
        return True
