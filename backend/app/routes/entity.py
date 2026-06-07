from fastapi import APIRouter, Depends, Path, Query

from app.services.entity_service import EntityService, get_entity_service
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate
from app.schemas.pagination import PaginatedResponse
from app.core.enums import EntityType

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("", response_model=EntityRead, status_code=201)
async def create_entity(
    entity_in: EntityCreate,
    service: EntityService = Depends(get_entity_service),
) -> EntityRead:
    """Create a new entity. Returns 409 if an entity with the same name exists."""
    return await service.create(entity_in)


@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(
    entity_id: int = Path(..., gt=0),
    service: EntityService = Depends(get_entity_service),
) -> EntityRead:
    """Get a specific entity by ID."""
    return await service.get(entity_id)


@router.get("", response_model=PaginatedResponse)
async def list_entities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EntityService = Depends(get_entity_service),
) -> dict:
    """List all entities with pagination."""
    return (await service.list_all(skip, limit)).to_dict(EntityRead)


@router.get("/filter/type/{entity_type}", response_model=PaginatedResponse)
async def get_entities_by_type(
    entity_type: EntityType = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EntityService = Depends(get_entity_service),
) -> dict:
    """Get entities filtered by type. `total` reflects only entities of this type."""
    return (await service.list_by_type(entity_type, skip, limit)).to_dict(EntityRead)


@router.get("/filter/country/{country_code}", response_model=PaginatedResponse)
async def get_entities_by_country(
    country_code: str = Path(..., min_length=2, max_length=2),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: EntityService = Depends(get_entity_service),
) -> dict:
    """Get entities filtered by ISO 3166-1 alpha-2 country code."""
    return (await service.list_by_country(country_code, skip, limit)).to_dict(EntityRead)


@router.get("/search/name/{name}", response_model=EntityRead)
async def get_entity_by_name(
    name: str = Path(...),
    service: EntityService = Depends(get_entity_service),
) -> EntityRead:
    """Search entity by exact name."""
    return await service.get_by_name(name)


@router.get("/search/ticker/{ticker}", response_model=EntityRead)
async def get_entity_by_ticker(
    ticker: str = Path(...),
    service: EntityService = Depends(get_entity_service),
) -> EntityRead:
    """Search entity by ticker symbol (substring match on comma-separated list)."""
    return await service.get_by_ticker(ticker)


@router.put("/{entity_id}", response_model=EntityRead)
async def update_entity(
    entity_id: int = Path(..., gt=0),
    entity_in: EntityUpdate = ...,
    service: EntityService = Depends(get_entity_service),
) -> EntityRead:
    """Partially update an existing entity. Returns 409 on name collision."""
    return await service.update(entity_id, entity_in)


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: int = Path(..., gt=0),
    service: EntityService = Depends(get_entity_service),
) -> None:
    """Delete an entity."""
    await service.delete(entity_id)
