"""HTTP client for the Dynamic World State microservice.

Calls the external world_state service (port 8006) to fetch geopolitical risk
scores, country-level state vectors, global dashboard data, and temporal
forecasts. Follows the same pattern as market_agents_client.py and kg_service.py.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WorldStateClient:
    """Thin HTTP client for the Dynamic World State API.

    Every method falls back gracefully to a sensible empty/default value when
    the world_state service is unreachable, so callers never need to handle
    connection errors.
    """

    def __init__(self, base_url: str = "") -> None:
        self._base_url = (base_url or settings.world_state_url).rstrip("/")

    # ── GET helpers ─────────────────────────────────────────────────────

    async def _get(self, path: str, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self._base_url}{path}")
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("world_state timed out on GET %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("world_state returned %s on GET %s: %s", e.response.status_code, path, e.response.text)
        except httpx.RequestError as e:
            logger.warning("world_state unreachable on GET %s: %s", path, e)
        return None

    async def _post(self, path: str, json: Any, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self._base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("world_state timed out on POST %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("world_state returned %s on POST %s: %s", e.response.status_code, path, e.response.text)
        except httpx.RequestError as e:
            logger.warning("world_state unreachable on POST %s: %s", path, e)
        return None

    # ── Public API methods ──────────────────────────────────────────────

    async def get_summary(self) -> dict[str, Any]:
        result = await self._get("/api/world-state/summary")
        return result or {}

    async def get_dashboard(self) -> dict[str, Any]:
        result = await self._get("/api/world-state/dashboard")
        return result or {}

    async def get_global_risk(self) -> dict[str, Any]:
        result = await self._get("/api/world-state/global-risk")
        return result or {}

    async def get_countries(self) -> dict[str, Any]:
        result = await self._get("/api/world-state/countries")
        return result or {"countries": []}

    async def get_country(self, country_id: str) -> dict[str, Any]:
        result = await self._get(f"/api/world-state/country/{country_id}")
        return result or {"error": f"country '{country_id}' not available"}

    async def get_regions(self) -> dict[str, Any]:
        result = await self._get("/api/world-state/regions")
        return result or {"regions": []}

    async def get_prediction(self) -> dict[str, Any]:
        result = await self._get("/api/world-state/prediction")
        return result or {"prediction": None}

    async def get_forecast(self, steps: int = 5) -> dict[str, Any]:
        result = await self._get(f"/api/world-state/forecast?steps={steps}")
        return result or {"forecast": []}

    async def get_snapshots(self, limit: int = 100) -> dict[str, Any]:
        result = await self._get(f"/api/world-state/snapshots?limit={limit}")
        return result or {"snapshots": []}

    async def ingest_event(self, event: dict[str, Any]) -> dict[str, Any]:
        result = await self._post("/api/world-state/ingest", json=event)
        return result or {"deltas_applied": 0}

    async def seed_demo_data(self) -> dict[str, Any]:
        result = await self._post("/api/world-state/seed", json={})
        return result or {"events_ingested": 0}


world_state_client = WorldStateClient()
