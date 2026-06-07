from datetime import datetime
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data_service import MarketDataService
from app.services.market_price_service import MarketPriceService, get_market_price_service
from app.schemas.market_price import MarketPriceCreate, MarketPriceRead
from app.schemas.pagination import PaginatedResponse
from app.database import get_db

router = APIRouter(prefix="/market-prices", tags=["market-prices"])


@router.post("", response_model=MarketPriceRead, status_code=201)
async def create_market_price(
    price_in: MarketPriceCreate,
    service: MarketPriceService = Depends(get_market_price_service),
) -> MarketPriceRead:
    """Create a new market price record (returns 409 on duplicate)."""
    return await service.create(price_in)


@router.get("/{price_id}", response_model=MarketPriceRead)
async def get_market_price(
    price_id: int = Path(..., gt=0),
    service: MarketPriceService = Depends(get_market_price_service),
) -> MarketPriceRead:
    """Get a specific market price record by ID."""
    return await service.get(price_id)


@router.get("/entity/{entity_id}", response_model=PaginatedResponse)
async def get_prices_by_entity(
    entity_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: MarketPriceService = Depends(get_market_price_service),
) -> dict:
    """Get all market prices for a specific entity with pagination."""
    return (await service.list_by_entity(entity_id, skip, limit)).to_dict(MarketPriceRead)


@router.get("/entity/{entity_id}/latest", response_model=MarketPriceRead)
async def get_latest_price(
    entity_id: int = Path(..., gt=0),
    service: MarketPriceService = Depends(get_market_price_service),
) -> MarketPriceRead:
    """Get the most recent market price for an entity."""
    return await service.get_latest(entity_id)


@router.get("/entity/{entity_id}/recent", response_model=list[MarketPriceRead])
async def get_recent_prices(
    entity_id: int = Path(..., gt=0),
    days: int = Query(30, ge=1, le=365),
    service: MarketPriceService = Depends(get_market_price_service),
) -> list[MarketPriceRead]:
    """Get market prices for an entity from the last N days."""
    return await service.get_recent(entity_id, days=days)


@router.get("/entity/{entity_id}/range", response_model=list[MarketPriceRead])
async def get_prices_by_date_range(
    entity_id: int = Path(..., gt=0),
    start_date: datetime = Query(..., description="Start date (ISO 8601 format)"),
    end_date: datetime = Query(..., description="End date (ISO 8601 format)"),
    service: MarketPriceService = Depends(get_market_price_service),
) -> list[MarketPriceRead]:
    """Get market prices for an entity within a date range."""
    return await service.get_range(entity_id, start_date, end_date)


# ---------------------------------------------------------------------------
# Market data ingestion via yfinance
# ---------------------------------------------------------------------------


@router.post(
    "/fetch/{entity_id}",
    response_model=dict,
    summary="Fetch and store market data from yfinance",
)
async def fetch_market_data(
    entity_id: int = Path(..., gt=0),
    period: str = Query(
        "1mo",
        description="Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
    ),
    interval: str = Query(
        "1d",
        description="Interval (1m, 2m, 5m, 15m, 30m, 60m, 1d, 5d, 1wk, 1mo)",
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch market prices from yfinance for an entity's ticker and store them."""
    data_service = MarketDataService(db)
    price_service = MarketPriceService(db)

    records = await data_service.fetch_and_store(
        entity_id=entity_id, period=period, interval=interval
    )

    stored = await price_service.bulk_create(records)

    return {
        "entity_id": entity_id,
        "records_fetched": len(records),
        "records_stored": len(stored),
        "source": "yfinance",
    }
