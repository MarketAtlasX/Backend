"""HTTP client for the Geopolitical Episodic Memory (GEM) microservice.

Calls the external memory service (port 8010) to create/search episodes,
find historical analogies, generate lessons, and track outcomes.
Follows the same pattern as world_state_client.py.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MemoryClient:
    """Thin HTTP client for the GEM service API.

    Every method falls back gracefully to a sensible default when the
    memory service is unreachable.
    """

    def __init__(self, base_url: str = "") -> None:
        self._base_url = (base_url or settings.memory_url).rstrip("/")

    async def _get(self, path: str, timeout: float = 10.0) -> dict[str, Any] | list[Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self._base_url}{path}")
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("memory timed out on GET %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("memory returned %s on GET %s: %s", e.response.status_code, path, e.response.text)
        except httpx.RequestError as e:
            logger.warning("memory unreachable on GET %s: %s", path, e)
        return None

    async def _post(self, path: str, json: Any, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self._base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("memory timed out on POST %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("memory returned %s on POST %s: %s", e.response.status_code, path, e.response.text)
        except httpx.RequestError as e:
            logger.warning("memory unreachable on POST %s: %s", path, e)
        return None

    async def _put(self, path: str, json: Any, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.put(f"{self._base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("memory timed out on PUT %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("memory returned %s on PUT %s: %s", e.response.status_code, path, e.response.text)
        except httpx.RequestError as e:
            logger.warning("memory unreachable on PUT %s: %s", path, e)
        return None

    async def _delete(self, path: str, timeout: float = 10.0) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.delete(f"{self._base_url}{path}")
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("memory timed out on DELETE %s", path)
        except httpx.HTTPStatusError as e:
            logger.warning("memory returned %s on DELETE %s: %s", e.response.status_code, path, e.response.text)
        except httpx.RequestError as e:
            logger.warning("memory unreachable on DELETE %s: %s", path, e)
        return None

    # ── Episodes ──────────────────────────────────────────────────────────

    async def create_episode(self, articles: list[dict], cluster_id: str | None = None) -> dict[str, Any]:
        params = f"?cluster_id={cluster_id}" if cluster_id else ""
        result = await self._post(f"/api/v1/memory/episodes{params}", json=articles)
        return result or {}

    async def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        return await self._get(f"/api/v1/memory/episodes/{episode_id}")

    async def list_episodes(self, limit: int = 20, offset: int = 0) -> list[Any]:
        result = await self._get(f"/api/v1/memory/episodes?limit={limit}&offset={offset}")
        return result if isinstance(result, list) else []

    async def update_episode(self, episode_id: str, articles: list[dict]) -> dict[str, Any]:
        result = await self._put(f"/api/v1/memory/episodes/{episode_id}", json=articles)
        return result or {}

    async def delete_episode(self, episode_id: str) -> dict[str, Any]:
        result = await self._delete(f"/api/v1/memory/episodes/{episode_id}")
        return result or {}

    # ── Search ────────────────────────────────────────────────────────────

    async def search(self, query: str, limit: int = 10) -> list[Any]:
        result = await self._get(f"/api/v1/memory/search?query={query}&limit={limit}")
        return result if isinstance(result, list) else []

    async def hybrid_search(self, query: str, limit: int = 10) -> list[Any]:
        result = await self._get(f"/api/v1/memory/search/hybrid?query={query}&limit={limit}")
        return result if isinstance(result, list) else []

    async def metadata_search(self, locations: str = "", sectors: str = "", limit: int = 10) -> list[Any]:
        result = await self._get(f"/api/v1/memory/search/metadata?locations={locations}&sectors={sectors}&limit={limit}")
        return result if isinstance(result, list) else []

    # ── Similarity & Analogy ──────────────────────────────────────────────

    async def find_similar(self, episode_id: str) -> list[Any]:
        result = await self._get(f"/api/v1/memory/similar/{episode_id}")
        return result if isinstance(result, list) else []

    async def find_analogous(self, episode_id: str) -> list[Any]:
        result = await self._get(f"/api/v1/memory/analogous/{episode_id}")
        return result if isinstance(result, list) else []

    # ── Outcomes ──────────────────────────────────────────────────────────

    async def record_outcome(self, episode_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        result = await self._post(f"/api/v1/memory/outcomes/{episode_id}", json=outcome)
        return result or {}

    async def get_outcomes(self, episode_id: str) -> dict[str, Any]:
        result = await self._get(f"/api/v1/memory/outcomes/{episode_id}")
        return result or {}

    async def analyze_outcomes(self, filters: dict[str, Any]) -> dict[str, Any]:
        result = await self._post("/api/v1/memory/outcomes/analyze", json=filters)
        return result or {}

    # ── Lessons ───────────────────────────────────────────────────────────

    async def generate_lessons(self, episode_id: str) -> dict[str, Any]:
        result = await self._post(f"/api/v1/memory/lessons/{episode_id}/generate", json={})
        return result or {}

    async def get_lessons(self, episode_id: str) -> list[Any]:
        result = await self._get(f"/api/v1/memory/lessons/{episode_id}")
        return result if isinstance(result, list) else []

    # ── Consolidation ─────────────────────────────────────────────────────

    async def consolidate(self) -> dict[str, Any]:
        result = await self._post("/api/v1/memory/consolidate", json={})
        return result or {}

    async def auto_consolidate(self) -> dict[str, Any]:
        result = await self._post("/api/v1/memory/consolidate/auto", json={})
        return result or {}

    # ── Analysis ──────────────────────────────────────────────────────────

    async def get_timeline(self, episode_id: str) -> dict[str, Any]:
        result = await self._get(f"/api/v1/memory/timeline/{episode_id}")
        return result or {}

    async def get_confidence(self, episode_id: str) -> dict[str, Any]:
        result = await self._get(f"/api/v1/memory/confidence/{episode_id}")
        return result or {}

    async def get_facts(self) -> list[Any]:
        result = await self._get("/api/v1/memory/facts")
        return result if isinstance(result, list) else []

    async def get_procedures(self) -> list[Any]:
        result = await self._get("/api/v1/memory/procedures")
        return result if isinstance(result, list) else []

    async def get_stats(self) -> dict[str, Any]:
        result = await self._get("/api/v1/memory/stats")
        return result or {}

    async def health(self) -> dict[str, Any]:
        result = await self._get("/api/v1/memory/health")
        return result or {"status": "unreachable"}


memory_client = MemoryClient()
