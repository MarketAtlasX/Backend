from fastapi import APIRouter, Depends, Path, Query

from app.services.signal_service import SignalService, get_signal_service
from app.schemas.signal import SignalCreate, SignalRead, SignalUpdate
from app.schemas.pagination import PaginatedResponse
from app.core.enums import SignalType, SignalStatus

_SERIALIZER = SignalRead

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("", response_model=SignalRead, status_code=201)
async def create_signal(
    signal_in: SignalCreate,
    service: SignalService = Depends(get_signal_service),
) -> SignalRead:
    """
    Create a new trading signal.

    Returns 404 if the referenced event_id or entity_id does not exist.
    """
    return await service.create(signal_in)


@router.get("/{signal_id}", response_model=SignalRead)
async def get_signal(
    signal_id: int = Path(..., gt=0),
    service: SignalService = Depends(get_signal_service),
) -> SignalRead:
    """Get a specific signal by ID."""
    return await service.get(signal_id)


@router.get("", response_model=PaginatedResponse)
async def list_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """List all signals with pagination."""
    return (await service.list_all(skip, limit)).to_dict(_SERIALIZER)


@router.get("/filter/event/{event_id}", response_model=PaginatedResponse)
async def get_signals_by_event(
    event_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """Get all signals generated from a specific event."""
    return (await service.list_by_event(event_id, skip, limit)).to_dict(_SERIALIZER)


@router.get("/filter/entity/{entity_id}", response_model=PaginatedResponse)
async def get_signals_by_entity(
    entity_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """Get all signals for a specific entity."""
    return (await service.list_by_entity(entity_id, skip, limit)).to_dict(_SERIALIZER)


@router.get("/filter/type/{signal_type}", response_model=PaginatedResponse)
async def get_signals_by_type(
    signal_type: SignalType = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """Get signals filtered by type (buy, sell, hold, short)."""
    return (await service.list_by_type(signal_type, skip, limit)).to_dict(_SERIALIZER)


@router.get("/filter/status/{status}", response_model=PaginatedResponse)
async def get_signals_by_status(
    status: SignalStatus = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """Get signals filtered by status (active, closed, expired)."""
    return (await service.list_by_status(status, skip, limit)).to_dict(_SERIALIZER)


@router.get("/filter/active", response_model=PaginatedResponse)
async def get_active_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """Get all currently active signals."""
    return (await service.list_active(skip, limit)).to_dict(_SERIALIZER)


@router.get("/filter/high-confidence", response_model=PaginatedResponse)
async def get_high_confidence_signals(
    min_confidence: float = Query(0.75, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SignalService = Depends(get_signal_service),
) -> dict:
    """Get signals with confidence at or above the given threshold."""
    return (await service.list_high_confidence(min_confidence, skip, limit)).to_dict(_SERIALIZER)


@router.put("/{signal_id}", response_model=SignalRead)
async def update_signal(
    signal_id: int = Path(..., gt=0),
    signal_in: SignalUpdate = ...,
    service: SignalService = Depends(get_signal_service),
) -> SignalRead:
    """Partially update an existing signal."""
    return await service.update(signal_id, signal_in)


@router.delete("/{signal_id}", status_code=204)
async def delete_signal(
    signal_id: int = Path(..., gt=0),
    service: SignalService = Depends(get_signal_service),
) -> None:
    """Delete a signal."""
    await service.delete(signal_id)
