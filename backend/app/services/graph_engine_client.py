from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GraphEngineClient:
    def __init__(self, base_url: str = "") -> None:
        self._base_url = (base_url or settings.graph_engine_url).rstrip("/")

    async def _get(self, path: str, params: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self._base_url}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("graph_engine timed out on GET %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("graph_engine returned %s on GET %s", e.response.status_code, path)
        except httpx.RequestError as e:
            logger.warning("graph_engine unreachable on GET %s: %s", path, e)
        return None

    async def health(self) -> dict[str, Any]:
        result = await self._get("/api/graph/health")
        return result or {"status": "unreachable"}

    async def forecast(self, symbol: str = "NVDA", company_name: str = "NVIDIA Corporation", current_price: float = 880.0) -> dict[str, Any]:
        result = await self._get("/api/graph/forecast", params={"symbol": symbol, "company_name": company_name, "current_price": current_price})
        return result or {}

    async def causal(self, root_event: str = "Iran Conflict", target_asset: str = "NVIDIA", max_paths: int = 5) -> dict[str, Any]:
        result = await self._get("/api/graph/causal", params={"root_event": root_event, "target_asset": target_asset, "max_paths": max_paths})
        return result or {}

    async def reasoning(self, target: str = "NVIDIA") -> dict[str, Any]:
        result = await self._get("/api/graph/reasoning", params={"target": target})
        return result or {}

    async def confidence(self, target: str = "NVIDIA", prediction_value: float | None = None, prediction_direction: str = "bullish") -> dict[str, Any]:
        params: dict[str, Any] = {"target": target, "prediction_direction": prediction_direction}
        if prediction_value is not None:
            params["prediction_value"] = prediction_value
        result = await self._get("/api/graph/confidence", params=params)
        return result or {}

    async def all(self, symbol: str = "NVDA", company_name: str = "NVIDIA Corporation", current_price: float = 880.0, root_event: str = "Iran Conflict", target_asset: str = "NVIDIA") -> dict[str, Any]:
        result = await self._get("/api/graph/all", params={"symbol": symbol, "company_name": company_name, "current_price": current_price, "root_event": root_event, "target_asset": target_asset})
        return result or {}


graph_engine_client = GraphEngineClient()
