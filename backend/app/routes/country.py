"""Country routes — both backend overview/news and frontend-facing globe API."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.country_repository import CountryRepository
from app.repositories.military_relation_repository import MilitaryRelationRepository
from app.repositories.port_repository import PortRepository
from app.repositories.trade_route_repository import TradeRouteRepository
from app.serializers import _military_relation_to_dict, _port_to_dict, _trade_route_to_dict
from app.services.country_service import get_country_kg_news, get_country_overview

router = APIRouter(prefix="/countries", tags=["countries"])


# ---------------------------------------------------------------------------
# Ordering: static paths first, then parameterized paths.
# Static paths MUST be registered BEFORE dynamic {code} paths so that
# FastAPI matches "/relations/trade" exactly rather than {code}="relations".
# Backend overview/news use integer IDs which don't conflict with string codes.
# ---------------------------------------------------------------------------


# --- Static paths (must precede /{code} to avoid {code} capturing "relations" / "ports") ---

@router.get("")
async def list_countries(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all countries with full profile data for the globe view."""
    repo = CountryRepository(db)
    countries = await repo.get_all_ordered(limit=200)
    return [_country_to_dict(c) for c in countries]


# --- Backend endpoints (existing) — use integer IDs ---

@router.get("/{country_id}/overview")
async def country_overview(
    country_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get core country data: info, events, companies, prices. Returns instantly."""
    try:
        return await get_country_overview(country_id, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Country not found")


@router.get("/{country_id}/news")
async def country_news(
    country_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get KG agent news + graph data for a country. Slower (~10s)."""
    try:
        return await get_country_kg_news(country_id, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Country not found")


# --- Parameterized code-based routes (ISO alpha-2) ---

@router.get("/{code}")
async def get_country_by_code(
    code: str = Path(..., min_length=2, max_length=2),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single country by ISO 3166-1 alpha-2 code."""
    repo = CountryRepository(db)
    country = await repo.get_by_code(code.upper())
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return _country_to_dict(country)


@router.get("/{code}/relations/trade")
async def get_country_trade_routes(
    code: str = Path(..., min_length=2, max_length=2),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get trade routes for a specific country."""
    repo = TradeRouteRepository(db)
    routes = await repo.get_by_country(code.upper())
    return [_trade_route_to_dict(r) for r in routes]


@router.get("/{code}/relations/military")
async def get_country_military_relations(
    code: str = Path(..., min_length=2, max_length=2),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get military/geopolitical relations for a specific country."""
    repo = MilitaryRelationRepository(db)
    relations = await repo.get_by_country(code.upper())
    return [_military_relation_to_dict(r) for r in relations]


@router.get("/{code}/ports")
async def get_country_ports(
    code: str = Path(..., min_length=2, max_length=2),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get major ports for a specific country."""
    repo = PortRepository(db)
    ports = await repo.get_by_country(code.upper())
    return [_port_to_dict(p) for p in ports]


# ---------------------------------------------------------------------------
# Serializers — match frontend TypeScript interfaces exactly
# ---------------------------------------------------------------------------


def _country_to_dict(c) -> dict:
    return {
        "code": c.code,
        "name": c.name,
        "region": c.region,
        "stockExchange": c.stock_exchange,
        "currency": c.currency,
        "currencySymbol": c.currency_symbol,
        "marketCap": c.market_cap,
        "tradingHours": c.trading_hours,
        "tickers": c.tickers.split(",") if c.tickers else [],
        "lat": c.latitude,
        "lng": c.longitude,
        "commodities": c.commodities.split(",") if c.commodities else [],
        "ports": c.port_names.split(",") if c.port_names else [],
    }



