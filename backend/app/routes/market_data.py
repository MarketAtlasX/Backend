"""Market data routes — per-sector return/volatility snapshot for the simulator."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.sector_data_service import SectorDataService

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/sectors")
async def get_sector_snapshot(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return the cached per-sector return/volatility snapshot.

    The snapshot is injected into simulator requests by the backend, so the
    simulator never calls this endpoint directly. Returns an empty snapshot
    (with `fallback: true`) when the live feed is unavailable — the simulator
    then falls back to its static sector betas.
    """
    service = SectorDataService(db)
    snapshot = await service.get_snapshot()
    if not snapshot:
        return {"fallback": True, "sectors": {}, "version": 1}
    return snapshot
