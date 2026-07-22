"""API routes that proxy requests to the Geopolitical Episodic Memory (GEM)
microservice.

All endpoints are mounted under ``/api/v1/memory`` so the frontend can call
``/api/memory/*`` (the Vite dev proxy rewrites ``/api`` → ``/api/v1``
transparently).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Query

from app.services.memory_client import memory_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# ── Health ──────────────────────────────────────────────────────────────


@router.get("/health")
async def health() -> dict[str, Any]:
    return await memory_client.health()


# ── Episodes ────────────────────────────────────────────────────────────


@router.post("/episodes")
async def create_episode(articles: list[dict], cluster_id: Optional[str] = Query(None)) -> dict[str, Any]:
    return await memory_client.create_episode(articles, cluster_id)


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: str) -> dict[str, Any] | None:
    return await memory_client.get_episode(episode_id)


@router.get("/episodes")
async def list_episodes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[Any]:
    return await memory_client.list_episodes(limit=limit, offset=offset)


@router.put("/episodes/{episode_id}")
async def update_episode(episode_id: str, articles: list[dict]) -> dict[str, Any]:
    return await memory_client.update_episode(episode_id, articles)


@router.delete("/episodes/{episode_id}")
async def delete_episode(episode_id: str) -> dict[str, Any]:
    return await memory_client.delete_episode(episode_id)


# ── Search ──────────────────────────────────────────────────────────────


@router.get("/search")
async def search(query: str, limit: int = Query(10, ge=1, le=50)) -> list[Any]:
    return await memory_client.search(query=query, limit=limit)


@router.get("/search/hybrid")
async def hybrid_search(query: str, limit: int = Query(10, ge=1, le=50)) -> list[Any]:
    return await memory_client.hybrid_search(query=query, limit=limit)


@router.get("/search/metadata")
async def metadata_search(
    locations: str = Query(""),
    sectors: str = Query(""),
    limit: int = Query(10, ge=1, le=50),
) -> list[Any]:
    return await memory_client.metadata_search(locations=locations, sectors=sectors, limit=limit)


# ── Similarity & Analogy ──────────────────────────────────────────────


@router.get("/similar/{episode_id}")
async def find_similar(episode_id: str) -> list[Any]:
    return await memory_client.find_similar(episode_id)


@router.get("/analogous/{episode_id}")
async def find_analogous(episode_id: str) -> list[Any]:
    return await memory_client.find_analogous(episode_id)


# ── Outcomes ───────────────────────────────────────────────────────────


@router.post("/outcomes/{episode_id}")
async def record_outcome(episode_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    return await memory_client.record_outcome(episode_id, outcome)


@router.get("/outcomes/{episode_id}")
async def get_outcomes(episode_id: str) -> dict[str, Any]:
    return await memory_client.get_outcomes(episode_id)


@router.post("/outcomes/analyze")
async def analyze_outcomes(filters: dict[str, Any]) -> dict[str, Any]:
    return await memory_client.analyze_outcomes(filters)


# ── Lessons ────────────────────────────────────────────────────────────


@router.post("/lessons/{episode_id}/generate")
async def generate_lessons(episode_id: str) -> dict[str, Any]:
    return await memory_client.generate_lessons(episode_id)


@router.get("/lessons/{episode_id}")
async def get_lessons(episode_id: str) -> list[Any]:
    return await memory_client.get_lessons(episode_id)


# ── Consolidation ──────────────────────────────────────────────────────


@router.post("/consolidate")
async def consolidate() -> dict[str, Any]:
    return await memory_client.consolidate()


@router.post("/consolidate/auto")
async def auto_consolidate() -> dict[str, Any]:
    return await memory_client.auto_consolidate()


# ── Analysis ────────────────────────────────────────────────────────────


@router.get("/timeline/{episode_id}")
async def get_timeline(episode_id: str) -> dict[str, Any]:
    return await memory_client.get_timeline(episode_id)


@router.get("/confidence/{episode_id}")
async def get_confidence(episode_id: str) -> dict[str, Any]:
    return await memory_client.get_confidence(episode_id)


@router.get("/facts")
async def get_facts() -> list[Any]:
    return await memory_client.get_facts()


@router.get("/procedures")
async def get_procedures() -> list[Any]:
    return await memory_client.get_procedures()


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    return await memory_client.get_stats()
