"""
EventService — business logic layer for Event domain operations.

Responsibilities:
  - Coordinate EventRepository calls.
  - Own the session commit / refresh lifecycle for mutations.
  - Raise HTTPException with meaningful details so routes stay thin.

Routes inject an EventService instance via Depends(get_event_service) and
call a single method per endpoint — no repository or session imports needed
in route handlers.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.event import Event
from app.repositories.event import EventRepository
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.pagination import Page
from app.core.enums import EventType, EventSeverity, EventStatus


class EventService:
    """Orchestrates all event-related business operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EventRepository(session)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, data: EventCreate) -> Event:
        """Persist a new event and return the refreshed ORM instance."""
        event = await self._repo.create(data.model_dump())
        await self._session.commit()
        await self._session.refresh(event)
        return event

    async def update(self, event_id: int, data: EventUpdate) -> Event:
        """
        Apply a partial update to an existing event.

        Raises 404 if the event does not exist.
        """
        update_data = data.model_dump(exclude_unset=True)
        event = await self._repo.update(event_id, update_data)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        await self._session.commit()
        await self._session.refresh(event)
        return event

    async def delete(self, event_id: int) -> None:
        """
        Permanently remove an event.

        Raises 404 if the event does not exist.
        """
        deleted = await self._repo.delete(event_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Event not found")
        await self._session.commit()

    # ------------------------------------------------------------------
    # Read operations — single record
    # ------------------------------------------------------------------

    async def get(self, event_id: int) -> Event:
        """Fetch a single event by ID. Raises 404 if not found."""
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    async def get_with_entities(self, event_id: int) -> Event:
        """Fetch a single event with its related entities eagerly loaded. Raises 404 if not found."""
        event = await self._repo.get_by_id_with_entities(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    # ------------------------------------------------------------------
    # Read operations — paginated lists
    # ------------------------------------------------------------------

    async def list_all(self, skip: int, limit: int) -> Page[Event]:
        """Return a paginated page of all events."""
        items = await self._repo.get_all(skip=skip, limit=limit)
        total = await self._repo.count()
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_type(self, event_type: EventType, skip: int, limit: int) -> Page[Event]:
        """Return a paginated page of events filtered by type."""
        items = await self._repo.get_by_type(event_type, skip=skip, limit=limit)
        total = await self._repo.count_by_type(event_type)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_severity(self, severity: EventSeverity, skip: int, limit: int) -> Page[Event]:
        """Return a paginated page of events filtered by severity."""
        items = await self._repo.get_by_severity(severity, skip=skip, limit=limit)
        total = await self._repo.count_by_severity(severity)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_status(self, status: EventStatus, skip: int, limit: int) -> Page[Event]:
        """Return a paginated page of events filtered by status."""
        items = await self._repo.get_by_status(status, skip=skip, limit=limit)
        total = await self._repo.count_by_status(status)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_recent(self, days: int, skip: int, limit: int) -> Page[Event]:
        """Return a paginated page of events from the last N days."""
        items = await self._repo.get_recent(days=days, skip=skip, limit=limit)
        total = await self._repo.count_recent(days=days)
        return Page(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------

def get_event_service(session: AsyncSession = Depends(get_db)) -> EventService:
    """Inject an EventService bound to the current request's DB session."""
    return EventService(session)
