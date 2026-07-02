"""Backtesting routes for signal validation."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.engine import Backtester
from app.database import get_db
from app.models.entity import Entity
from app.models.event import Event
from app.models.market_price import MarketPrice

router = APIRouter(prefix="/backtest", tags=["backtesting"])


@router.get("/run")
async def run_backtest(
    entity_id: int = Query(..., description="Entity ID to backtest"),
    days: int = Query(365, ge=30, le=3650, description="Lookback days"),
    db: AsyncSession = Depends(get_db),
):
    # Fetch entity
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    ticker = entity.ticker_symbols.split(",")[0].strip() if entity.ticker_symbols else "UNKNOWN"

    # Fetch historical events linked to this entity
    from app.models.event_entity import EventEntity
    cutoff = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(Event)
        .join(EventEntity, EventEntity.event_id == Event.id)
        .where(EventEntity.entity_id == entity_id)
        .where(Event.event_date >= cutoff)
        .order_by(Event.event_date)
    )
    events = result.scalars().all()

    # Fetch price history
    result = await db.execute(
        select(MarketPrice)
        .where(MarketPrice.entity_id == entity_id)
        .where(MarketPrice.price_date >= cutoff)
        .order_by(MarketPrice.price_date)
    )
    prices = result.scalars().all()

    if not prices:
        raise HTTPException(status_code=400, detail="No price data available for backtesting")

    historical_events = [
        {
            "event_id": e.id,
            "date": e.event_date.isoformat() if e.event_date else "",
            "title": e.title,
            "description": e.description or "",
            "event_type": e.event_type,
            "severity": _severity_to_float(e.severity),
        }
        for e in events
    ]

    price_history = [
        {"date": p.price_date.isoformat(), "close": float(p.close_price)}
        for p in prices
    ]

    backtester = Backtester(lookback_days=days)
    result = await backtester.run(historical_events, price_history, ticker)

    return {
        "entity_id": entity_id,
        "ticker": ticker,
        "entity_name": entity.name,
        "events_analyzed": len(events),
        "price_points": len(prices),
        "period_days": days,
        "results": result.summary(),
    }


def _severity_to_float(severity: str) -> float:
    mapping = {"low": 0.2, "medium": 0.5, "high": 0.7, "critical": 0.9}
    return mapping.get(str(severity).lower(), 0.5)
