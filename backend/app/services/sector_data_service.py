"""Sector market-data service.

Computes per-sector 30-day return and volatility from a predefined
sector → ticker map (see config.SECTOR_TICKERS). Results are cached in
Redis (fast) and the `sector_cache` table (durable, TTL-aware) so repeated
simulations don't recompute expensive API calls.

When live data is unavailable (no API key, provider down), the service
returns an empty snapshot and callers gracefully fall back to the
simulator's static betas.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache
from app.config import settings
from app.models.portfolio import SectorCache
from app.services.financial_data_service import get_price_history

logger = logging.getLogger(__name__)

SECTOR_SNAPSHOT_CACHE_KEY = "sector:snapshot"


def _parse_sector_map(raw: str) -> dict[str, list[str]]:
    """Parse 'sector:t1,t2;sector2:t3' into {sector: [tickers]}."""
    mapping: dict[str, list[str]] = {}
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        sector, _, tickers = chunk.partition(":")
        sector = sector.strip().lower().replace(" ", "_")
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if sector and ticker_list:
            mapping[sector] = ticker_list
    return mapping


def _compute_metrics(history: list[dict[str, Any]]) -> dict[str, float] | None:
    """Compute 30-day return (%) and daily-volatility annualized from OHLCV rows."""
    if not history or len(history) < 2:
        return None
    closes = [float(row["close"]) for row in history[:30] if row.get("close")]
    if len(closes) < 2 or any(c <= 0 for c in closes):
        return None

    first, last = closes[-1], closes[0]
    return_pct = (last / first - 1.0) * 100.0

    log_returns = [
        math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0
    ]
    if not log_returns:
        return None
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
    daily_vol = math.sqrt(variance)
    annualized_vol = daily_vol * math.sqrt(252) * 100.0

    return {"return_pct": round(return_pct, 4), "volatility": round(annualized_vol, 4)}


class SectorDataService:
    """Computes and caches per-sector return/volatility metrics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_snapshot(self) -> dict[str, Any]:
        """Return the full sector snapshot, using cache when fresh.

        Shape: {"version": 1, "sectors": {sector: {return_pct, volatility}}, "snapshot_time": iso}
        Returns an empty dict on failure (callers fall back to static betas).
        """
        cached = await cache.get(SECTOR_SNAPSHOT_CACHE_KEY)
        if cached:
            return cached

        db_snapshot = await self._fresh_db_snapshot()
        if db_snapshot is not None:
            await cache.set(
                SECTOR_SNAPSHOT_CACHE_KEY, db_snapshot, ttl=settings.sector_cache_ttl_seconds
            )
            return db_snapshot

        # Live recompute (sector_cache table has no fresh rows).
        snapshot = await self._compute_snapshot_live()
        if snapshot:
            await self._persist_snapshot(snapshot)
            await cache.set(
                SECTOR_SNAPSHOT_CACHE_KEY, snapshot, ttl=settings.sector_cache_ttl_seconds
            )
        return snapshot

    async def _fresh_db_snapshot(self) -> dict[str, Any] | None:
        now = datetime.utcnow()
        result = await self.db.execute(select(SectorCache).where(SectorCache.expires_at > now))
        rows = result.scalars().all()
        if not rows:
            return None
        sectors = {
            row.sector: {"return_pct": row.return_pct, "volatility": row.volatility} for row in rows
        }
        latest = max((r.expires_at for r in rows), default=now)
        return {
            "version": 1,
            "sectors": sectors,
            "snapshot_time": latest.isoformat(),
        }

    async def _compute_snapshot_live(self) -> dict[str, Any]:
        mapping = _parse_sector_map(settings.sector_tickers)
        sectors: dict[str, Any] = {}
        for sector, tickers in mapping.items():
            metrics = await self._sector_metrics(tickers)
            if metrics:
                sectors[sector] = metrics
        if not sectors:
            return {}
        return {
            "version": 1,
            "sectors": sectors,
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
        }

    async def _sector_metrics(self, tickers: list[str]) -> dict[str, float] | None:
        for ticker in tickers:
            history = await get_price_history(ticker, interval="daily", outputsize="compact")
            metrics = _compute_metrics(history or [])
            if metrics:
                return metrics
        return None

    async def _persist_snapshot(self, snapshot: dict[str, Any]) -> None:
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=settings.sector_cache_ttl_seconds)
        try:
            for sector, metrics in snapshot.get("sectors", {}).items():
                row = await self.db.execute(select(SectorCache).where(SectorCache.sector == sector))
                existing = row.scalar_one_or_none()
                if existing:
                    existing.return_pct = metrics["return_pct"]
                    existing.volatility = metrics["volatility"]
                    existing.computed_at = now
                    existing.expires_at = expires_at
                else:
                    self.db.add(
                        SectorCache(
                            sector=sector,
                            return_pct=metrics["return_pct"],
                            volatility=metrics["volatility"],
                            computed_at=now,
                            expires_at=expires_at,
                        )
                    )
            await self.db.commit()
        except Exception as e:
            logger.warning("Failed to persist sector snapshot: %s", e)


def get_sector_data_service(db: AsyncSession = None) -> SectorDataService:
    return SectorDataService(db)


async def get_sector_snapshot() -> dict[str, Any]:
    """Module-level snapshot helper — opens its own session.

    Used by the chatbot context builder and other non-route callers.
    Returns an empty snapshot on failure so callers never crash.
    """
    from app.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            service = SectorDataService(db)
            snapshot = await service.get_snapshot()
            if snapshot:
                return snapshot
    except Exception as e:
        logger.warning("Sector snapshot unavailable: %s", e)
    return {"fallback": True, "sectors": {}, "version": 1}
