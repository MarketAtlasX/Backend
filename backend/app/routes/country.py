"""Country overview and news endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.country_service import get_country_overview, get_country_kg_news

router = APIRouter(prefix="/countries", tags=["countries"])


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
