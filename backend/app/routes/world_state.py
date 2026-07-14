"""API routes that proxy requests to the Dynamic World State microservice.

All endpoints are mounted under ``/api/v1/world-state`` so the frontend
can call ``/api/world-state/*`` (the Vite dev proxy rewrites ``/api`` →
``/api/v1`` transparently).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from app.services.world_state_client import world_state_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/world-state", tags=["world-state"])


@router.get("/summary")
async def get_summary() -> dict[str, Any]:
    return await world_state_client.get_summary()


@router.get("/dashboard")
async def get_dashboard() -> dict[str, Any]:
    return await world_state_client.get_dashboard()


@router.get("/global-risk")
async def get_global_risk() -> dict[str, Any]:
    return await world_state_client.get_global_risk()


@router.get("/countries")
async def get_countries() -> dict[str, Any]:
    return await world_state_client.get_countries()


@router.get("/country/{country_id}")
async def get_country(country_id: str) -> dict[str, Any]:
    return await world_state_client.get_country(country_id)


@router.get("/regions")
async def get_regions() -> dict[str, Any]:
    return await world_state_client.get_regions()


@router.get("/prediction")
async def get_prediction() -> dict[str, Any]:
    return await world_state_client.get_prediction()


@router.get("/forecast")
async def get_forecast(steps: int = Query(5, ge=1, le=30)) -> dict[str, Any]:
    return await world_state_client.get_forecast(steps=steps)


@router.get("/snapshots")
async def get_snapshots(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    return await world_state_client.get_snapshots(limit=limit)


@router.post("/ingest")
async def ingest_event(event: dict[str, Any]) -> dict[str, Any]:
    return await world_state_client.ingest_event(event)


@router.post("/seed")
async def seed_demo_data() -> dict[str, Any]:
    return await world_state_client.seed_demo_data()
