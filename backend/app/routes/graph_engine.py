from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Query

from app.services.graph_engine_client import graph_engine_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph-engine", tags=["graph-engine"])


@router.get("/health")
async def get_health() -> dict[str, Any]:
    return await graph_engine_client.health()


@router.get("/forecast")
async def get_forecast(
    symbol: str = Query("NVDA"),
    company_name: str = Query("NVIDIA Corporation"),
    current_price: float = Query(880.0),
) -> dict[str, Any]:
    return await graph_engine_client.forecast(symbol, company_name, current_price)


@router.get("/causal")
async def get_causal(
    root_event: str = Query("Iran Conflict"),
    target_asset: str = Query("NVIDIA"),
    max_paths: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    return await graph_engine_client.causal(root_event, target_asset, max_paths)


@router.get("/reasoning")
async def get_reasoning(
    target: str = Query("NVIDIA"),
) -> dict[str, Any]:
    return await graph_engine_client.reasoning(target)


@router.get("/confidence")
async def get_confidence(
    target: str = Query("NVIDIA"),
    prediction_value: Optional[float] = None,
    prediction_direction: str = Query("bullish"),
) -> dict[str, Any]:
    return await graph_engine_client.confidence(target, prediction_value, prediction_direction)


@router.get("/all")
async def get_all(
    symbol: str = Query("NVDA"),
    company_name: str = Query("NVIDIA Corporation"),
    current_price: float = Query(880.0),
    root_event: str = Query("Iran Conflict"),
    target_asset: str = Query("NVIDIA"),
) -> dict[str, Any]:
    return await graph_engine_client.all(symbol, company_name, current_price, root_event, target_asset)
