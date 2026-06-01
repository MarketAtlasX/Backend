from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.entity import EntityRepository
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("", response_model=EntityRead, status_code=201)
async def create_entity(
    entity_in: EntityCreate,
    db: AsyncSession = Depends(get_db),
) -> EntityRead:
    """Create a new entity."""
    repo = EntityRepository(db)
    existing = await repo.get_by_name(entity_in.name)
    if existing:
        raise HTTPException(status_code=409, detail="Entity with this name already exists")
    
    entity = await repo.create(entity_in.model_dump())
    await db.commit()
    await db.refresh(entity)
    return entity


@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(
    entity_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> EntityRead:
    """Get a specific entity by ID."""
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("", response_model=PaginatedResponse)
async def list_entities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all entities with pagination."""
    repo = EntityRepository(db)
    entities = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": entities,
    }


@router.get("/type/{entity_type}", response_model=PaginatedResponse)
async def get_entities_by_type(
    entity_type: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get entities filtered by type (country, company, person, region)."""
    repo = EntityRepository(db)
    entities = await repo.get_by_type(entity_type, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": entities,
    }


@router.get("/search/name/{name}", response_model=EntityRead)
async def get_entity_by_name(
    name: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> EntityRead:
    """Search entity by name."""
    repo = EntityRepository(db)
    entity = await repo.get_by_name(name)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/search/ticker/{ticker}", response_model=EntityRead)
async def get_entity_by_ticker(
    ticker: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> EntityRead:
    """Search entity by ticker symbol."""
    repo = EntityRepository(db)
    entity = await repo.get_by_ticker(ticker)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity with this ticker not found")
    return entity


@router.get("/country/{country_code}", response_model=PaginatedResponse)
async def get_entities_by_country(
    country_code: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get entities filtered by country code (ISO 3166-1 alpha-2)."""
    repo = EntityRepository(db)
    entities = await repo.get_by_country_code(country_code, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": entities,
    }


@router.put("/{entity_id}", response_model=EntityRead)
async def update_entity(
    entity_id: int = Path(..., gt=0),
    entity_in: EntityUpdate = None,
    db: AsyncSession = Depends(get_db),
) -> EntityRead:
    """Update an existing entity."""
    repo = EntityRepository(db)
    update_data = entity_in.model_dump(exclude_unset=True)
    entity = await repo.update(entity_id, update_data)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    await db.commit()
    await db.refresh(entity)
    return entity


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an entity."""
    repo = EntityRepository(db)
    success = await repo.delete(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    await db.commit()
