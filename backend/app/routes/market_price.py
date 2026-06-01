from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.market_price import MarketPriceRepository
from app.schemas.market_price import MarketPriceCreate, MarketPriceRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/market-prices", tags=["market-prices"])


@router.post("", response_model=MarketPriceRead, status_code=201)
async def create_market_price(
    price_in: MarketPriceCreate,
    db: AsyncSession = Depends(get_db),
) -> MarketPriceRead:
    """Create a new market price record (prevents duplicates)."""
    repo = MarketPriceRepository(db)
    
    exists = await repo.exists(price_in.entity_id, price_in.price_date)
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Market price for this entity on this date already exists"
        )
    
    price = await repo.create(price_in.model_dump())
    await db.commit()
    await db.refresh(price)
    return price


@router.get("/{price_id}", response_model=MarketPriceRead)
async def get_market_price(
    price_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> MarketPriceRead:
    """Get a specific market price record by ID."""
    repo = MarketPriceRepository(db)
    price = await repo.get_by_id(price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Market price not found")
    return price


@router.get("/entity/{entity_id}", response_model=PaginatedResponse)
async def get_prices_by_entity(
    entity_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all market prices for a specific entity."""
    repo = MarketPriceRepository(db)
    prices = await repo.get_by_entity_id(entity_id, skip=skip, limit=limit)
    total = await repo.count()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": prices,
    }


@router.get("/entity/{entity_id}/latest", response_model=MarketPriceRead)
async def get_latest_price(
    entity_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
) -> MarketPriceRead:
    """Get the most recent market price for an entity."""
    repo = MarketPriceRepository(db)
    price = await repo.get_latest_by_entity(entity_id)
    if not price:
        raise HTTPException(status_code=404, detail="No market prices found for this entity")
    return price


@router.get("/entity/{entity_id}/recent", response_model=PaginatedResponse)
async def get_recent_prices(
    entity_id: int = Path(..., gt=0),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get market prices for an entity from the last N days."""
    repo = MarketPriceRepository(db)
    prices = await repo.get_recent_by_entity(entity_id, days=days)
    return {
        "total": len(prices),
        "skip": 0,
        "limit": len(prices),
        "items": prices,
    }


@router.get("/entity/{entity_id}/range", response_model=PaginatedResponse)
async def get_prices_by_date_range(
    entity_id: int = Path(..., gt=0),
    start_date: datetime = Query(..., description="Start date (ISO 8601 format)"),
    end_date: datetime = Query(..., description="End date (ISO 8601 format)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get market prices for an entity within a date range."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    repo = MarketPriceRepository(db)
    prices = await repo.get_by_date_range(entity_id, start_date, end_date)
    return {
        "total": len(prices),
        "skip": 0,
        "limit": len(prices),
        "items": prices,
    }
