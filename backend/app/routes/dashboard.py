"""Aggregated dashboard endpoint providing summary statistics.

Returns counts and recent items across all domain models in a single request,
reducing frontend waterfall requests.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entity import Entity
from app.models.event import Event
from app.models.signal import Signal

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregated platform statistics for the frontend dashboard.

    Returns counts and recent items in a single response.
    """
    event_count = await _count(db, Event)
    entity_count = await _count(db, Entity)
    signal_count = await _count(db, Signal)
    active_signals = await _count_where(
        db, Signal, Signal.status == "active"
    )
    countries = await _count_where(
        db, Entity, Entity.entity_type == "country"
    )
    companies = await _count_where(
        db, Entity, Entity.entity_type == "company"
    )

    return {
        "total_events": event_count,
        "total_entities": entity_count,
        "total_signals": signal_count,
        "active_signals": active_signals,
        "countries": countries,
        "companies": companies,
    }


async def _count(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar_one()


async def _count_where(db: AsyncSession, model, condition) -> int:
    result = await db.execute(
        select(func.count()).select_from(model).where(condition)
    )
    return result.scalar_one()
