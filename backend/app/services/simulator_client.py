"""HTTP client for the Scenario Simulator microservice (port 8007).

The simulator is a pure compute engine: the backend supplies the scenario,
portfolio allocation, and sector metrics *in the request body*. The simulator
never fetches from the backend. All methods fall back gracefully when the
simulator is unreachable.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SIM_TIMEOUT = 300.0  # simulations can take a while


class SimulatorClient:
    """Thin HTTP client for the MarketAtlas Scenario Simulator API."""

    def __init__(self, base_url: str = "") -> None:
        self._base_url = (base_url or settings.simulator_url).rstrip("/")

    async def _post(
        self, path: str, json: Any, timeout: float = SIM_TIMEOUT
    ) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self._base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("simulator timed out on POST %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning(
                "simulator returned %s on POST %s: %s",
                e.response.status_code,
                path,
                e.response.text,
            )
        except httpx.RequestError as e:
            logger.warning("simulator unreachable on POST %s: %s", path, e)
        return None

    async def _get(self, path: str, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self._base_url}{path}")
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("simulator timed out on GET %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning(
                "simulator returned %s on GET %s: %s", e.response.status_code, path, e.response.text
            )
        except httpx.RequestError as e:
            logger.warning("simulator unreachable on GET %s: %s", path, e)
        return None

    async def create_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        return (await self._post("/api/simulation/create", json=scenario)) or {}

    async def run_simulation(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._post("/api/simulation/run", json=payload)
        return result or {}

    async def get_simulation(self, simulation_id: str) -> dict[str, Any]:
        return (await self._get(f"/api/simulation/{simulation_id}")) or {}

    async def get_report(self, simulation_id: str) -> dict[str, Any]:
        return (await self._get(f"/api/simulation/{simulation_id}/report")) or {}

    async def get_portfolio(
        self,
        simulation_id: str,
        allocation: dict[str, float],
        horizon_days: int = 90,
        sector_data: dict | None = None,
    ) -> dict[str, Any]:
        result = await self._post(
            f"/api/simulation/{simulation_id}/portfolio",
            json={
                "horizon_days": horizon_days,
                "portfolio_allocation": allocation,
                "sector_data": sector_data or {},
            },
        )
        return result or {}

    async def health(self) -> dict[str, Any]:
        return (await self._get("/api/simulation/health")) or {}


simulator_client = SimulatorClient()
