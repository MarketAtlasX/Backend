from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.signal import SignalRepository
from app.schemas.signal import SignalCreate, SignalRead, SignalUpdate
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("", response_model=SignalRead, status_code=201)
async def create_signal(
    signal_in: SignalCreate,
    db: AsyncSession = Depends(get_db),
) -> SignalRead:
    """Create a new trading signal."""
    repo = SignalRepository(db)
    signal = await repo.create(signal_in.model_dump())
    await db.commit()
    await db.refresh(signal)
    return signal


@router.get("/{signal_id}", response_model=SignalRead)
async def get_signal(
    signal_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> SignalRead:
    """Get a specific signal by ID."""
    repo = SignalRepository(db)
    signal = await repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.get("", response_model=PaginatedResponse)
async def list_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all signals with pagination."""
    repo = SignalRepository(db)
    signals = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.get("/event/{event_id}", response_model=PaginatedResponse)
async def get_signals_by_event(
    event_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all signals generated from a specific event."""
    repo = SignalRepository(db)
    signals = await repo.get_by_event_id(event_id, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.get("/entity/{entity_id}", response_model=PaginatedResponse)
async def get_signals_by_entity(
    entity_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all signals for a specific entity."""
    repo = SignalRepository(db)
    signals = await repo.get_by_entity_id(entity_id, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.get("/type/{signal_type}", response_model=PaginatedResponse)
async def get_signals_by_type(
    signal_type: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get signals filtered by type (buy, sell, hold, short)."""
    repo = SignalRepository(db)
    signals = await repo.get_by_type(signal_type, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.get("/status/{status}", response_model=PaginatedResponse)
async def get_signals_by_status(
    status: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get signals filtered by status (active, closed, expired)."""
    repo = SignalRepository(db)
    signals = await repo.get_by_status(status, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.get("/active/high-confidence", response_model=PaginatedResponse)
async def get_high_confidence_signals(
    min_confidence: float = Query(0.75, ge=0, le=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get active signals with confidence above threshold."""
    repo = SignalRepository(db)
    signals = await repo.get_high_confidence(min_confidence, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.get("/active/all", response_model=PaginatedResponse)
async def get_active_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all active signals."""
    repo = SignalRepository(db)
    signals = await repo.get_active(skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": signals,
    }


@router.put("/{signal_id}", response_model=SignalRead)
async def update_signal(
    signal_id: int = Path(..., gt=0),
    signal_in: SignalUpdate = None,
    db: AsyncSession = Depends(get_db),
) -> SignalRead:
    """Update an existing signal."""
    repo = SignalRepository(db)
    update_data = signal_in.model_dump(exclude_unset=True)
    signal = await repo.update(signal_id, update_data)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    await db.commit()
    await db.refresh(signal)
    return signal


@router.delete("/{signal_id}", status_code=204)
async def delete_signal(
    signal_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a signal."""
    repo = SignalRepository(db)
    success = await repo.delete(signal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Signal not found")
    await db.commit()
