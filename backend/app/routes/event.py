from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_service import EventService, get_event_service
from app.schemas.event import EventCreate, EventRead, EventUpdate, EventReadWithEntities
from app.schemas.pagination import PaginatedResponse
from app.core.enums import EventType, EventSeverity, EventStatus

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    event_in: EventCreate,
    service: EventService = Depends(get_event_service),
) -> EventRead:
    """Create a new event."""
    return await service.create(event_in)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int = Path(..., gt=0),
    service: EventService = Depends(get_event_service),
) -> EventRead:
    """Get a specific event by ID."""
    return await service.get(event_id)


@router.get("/{event_id}/entities", response_model=EventReadWithEntities)
async def get_event_with_entities(
    event_id: int = Path(..., gt=0),
    service: EventService = Depends(get_event_service),
) -> EventReadWithEntities:
    """Get a specific event including its related entities."""
    return await service.get_with_entities(event_id)


@router.get("", response_model=PaginatedResponse)
async def list_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    service: EventService = Depends(get_event_service),
) -> dict:
    """List all events with pagination."""
    return (await service.list_all(skip, limit)).to_dict(EventRead)


@router.get("/filter/type/{event_type}", response_model=PaginatedResponse)
async def get_events_by_type(
    event_type: EventType = Path(..., description="Event type to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EventService = Depends(get_event_service),
) -> dict:
    """Get events filtered by type. `total` reflects only events of this type."""
    return (await service.list_by_type(event_type, skip, limit)).to_dict(EventRead)


@router.get("/filter/severity/{severity}", response_model=PaginatedResponse)
async def get_events_by_severity(
    severity: EventSeverity = Path(..., description="Severity level to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EventService = Depends(get_event_service),
) -> dict:
    """Get events filtered by severity. `total` reflects only events of this severity."""
    return (await service.list_by_severity(severity, skip, limit)).to_dict(EventRead)


@router.get("/filter/status/{status}", response_model=PaginatedResponse)
async def get_events_by_status(
    status: EventStatus = Path(..., description="Status to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EventService = Depends(get_event_service),
) -> dict:
    """Get events filtered by status. `total` reflects only events of this status."""
    return (await service.list_by_status(status, skip, limit)).to_dict(EventRead)


@router.get("/filter/recent/{days}", response_model=PaginatedResponse)
async def get_recent_events(
    days: int = Path(..., ge=1, le=365, description="Number of days to look back"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EventService = Depends(get_event_service),
) -> dict:
    """Get recent events from the last N days. `total` reflects only events in that window."""
    return (await service.list_recent(days, skip, limit)).to_dict(EventRead)


@router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int = Path(..., gt=0),
    event_in: EventUpdate = ...,
    service: EventService = Depends(get_event_service),
) -> EventRead:
    """Partially update an existing event."""
    return await service.update(event_id, event_in)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: int = Path(..., gt=0),
    service: EventService = Depends(get_event_service),
) -> None:
    """Delete an event."""
    await service.delete(event_id)


# ---------------------------------------------------------------------------
# Event-Entity association endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{event_id}/entities/{entity_id}",
    status_code=204,
    description="Link an entity to an event",
)
async def link_entity_to_event(
    event_id: int = Path(..., gt=0),
    entity_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Link an existing entity to an existing event."""
    from app.models.event_entity import EventEntity
    from app.repositories.event import EventRepository
    from app.repositories.entity import EntityRepository

    event_repo = EventRepository(db)
    entity_repo = EntityRepository(db)

    event = await event_repo.get_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    entity = await entity_repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    from sqlalchemy import select

    existing_query = select(EventEntity).where(
        EventEntity.event_id == event_id, EventEntity.entity_id == entity_id
    )
    result = await db.execute(existing_query)
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Entity is already linked to this event",
        )

    link = EventEntity(event_id=event_id, entity_id=entity_id)
    db.add(link)
    await db.commit()


@router.delete(
    "/{event_id}/entities/{entity_id}",
    status_code=204,
    description="Unlink an entity from an event",
)
async def unlink_entity_from_event(
    event_id: int = Path(..., gt=0),
    entity_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove the link between an entity and an event."""
    from app.models.event_entity import EventEntity
    from sqlalchemy import select

    query = select(EventEntity).where(
        EventEntity.event_id == event_id, EventEntity.entity_id == entity_id
    )
    result = await db.execute(query)
    link = result.scalars().first()

    if link is None:
        raise HTTPException(
            status_code=404,
            detail="Entity is not linked to this event",
        )

    await db.delete(link)
    await db.commit()
