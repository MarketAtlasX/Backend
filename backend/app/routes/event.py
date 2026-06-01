from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.event import EventRepository
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    event_in: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> EventRead:
    """Create a new event."""
    repo = EventRepository(db)
    event = await repo.create(event_in.model_dump())
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> EventRead:
    """Get a specific event by ID."""
    repo = EventRepository(db)
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("", response_model=PaginatedResponse)
async def list_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all events with pagination."""
    repo = EventRepository(db)
    events = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": events,
    }


@router.get("/type/{event_type}", response_model=PaginatedResponse)
async def get_events_by_type(
    event_type: str = Path(..., description="Event type to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get events filtered by type."""
    repo = EventRepository(db)
    events = await repo.get_by_type(event_type, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": events,
    }


@router.get("/severity/{severity}", response_model=PaginatedResponse)
async def get_events_by_severity(
    severity: str = Path(..., description="Severity level to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get events filtered by severity."""
    repo = EventRepository(db)
    events = await repo.get_by_severity(severity, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": events,
    }


@router.get("/recent/{days}", response_model=PaginatedResponse)
async def get_recent_events(
    days: int = Path(..., ge=1, le=365, description="Number of days to look back"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get recent events from the last N days."""
    repo = EventRepository(db)
    events = await repo.get_recent(days=days, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": events,
    }


@router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int = Path(..., gt=0),
    event_in: EventUpdate = None,
    db: AsyncSession = Depends(get_db),
) -> EventRead:
    """Update an existing event."""
    repo = EventRepository(db)
    update_data = event_in.model_dump(exclude_unset=True)
    event = await repo.update(event_id, update_data)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an event."""
    repo = EventRepository(db)
    success = await repo.delete(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.commit()
