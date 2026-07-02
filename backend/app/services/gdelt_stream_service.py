"""Real-time geopolitical news streaming via GDELT DOC 2.0 API.

Polls the GDELT DOC API every 60 seconds for the latest articles, creates
Event records for new articles, and broadcasts them to WebSocket clients.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from app.services.event_broadcaster import EventBroadcaster
from app.services.event_ingestion_service import _classify_event, _parse_date

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERY = "geopolitics"
POLL_INTERVAL = 120


class GDELTStreamService:
    """Polls GDELT every 60s, creates Event records, and broadcasts them."""

    def __init__(self, broadcaster: EventBroadcaster) -> None:
        self._broadcaster = broadcaster
        self._seen_urls: set[str] = set()
        self._http = httpx.AsyncClient(timeout=15)

    async def run(self) -> None:
        logger.info("Starting GDELT stream (poll every %ds)", POLL_INTERVAL)
        await self._load_existing_urls()

        while True:
            try:
                articles = await self._fetch_recent()
                for article in articles:
                    await self._process_article(article)
            except Exception:
                logger.exception("GDELT poll cycle failed")
            await asyncio.sleep(POLL_INTERVAL)

    async def _load_existing_urls(self) -> None:
        from app.database import AsyncSessionLocal
        from app.repositories.event import EventRepository

        try:
            async with AsyncSessionLocal() as db:
                repo = EventRepository(db)
                events = await repo.get_all(limit=5000)
                for ev in events:
                    if ev.source_url:
                        self._seen_urls.add(ev.source_url)
            logger.info("Loaded %d existing event URLs for dedup", len(self._seen_urls))
        except Exception:
            logger.exception("Failed to load existing URLs")

    async def _fetch_recent(self) -> list[dict[str, Any]]:
        params = {
            "query": GDELT_QUERY,
            "mode": "artlist",
            "format": "json",
            "maxrecords": 15,
            "sort": "datedesc",
            "lastminutes": 10,
        }
        for attempt in range(3):
            resp = await self._http.get(GDELT_URL, params=params)
            if resp.status_code == 429:
                wait = 2 ** (attempt + 3)
                logger.warning("GDELT rate limited, retrying in %ds", wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data.get("articles", [])
        return []

    async def _process_article(self, article: dict[str, Any]) -> None:
        url = article.get("url", "")
        title = article.get("title", "")
        if not url or not title:
            return

        if url in self._seen_urls:
            return
        self._seen_urls.add(url)

        event = await self._create_event(article)
        if event is None:
            return

        await self._broadcaster.broadcast_event(event)

    async def _create_event(self, article: dict[str, Any]) -> dict[str, Any] | None:
        from app.database import AsyncSessionLocal
        from app.repositories.entity import EntityRepository
        from app.repositories.event import EventRepository
        from app.repositories.event_entity import EventEntityRepository

        title = article.get("title", "")[:255]
        content = article.get("content") or article.get("title", "")
        source = article.get("domain", "gdelt")[:255] or "gdelt"
        source_url = article.get("url", "")

        seendate = article.get("seendate", "")
        event_date = _parse_date(seendate) or datetime.utcnow()
        event_type = _classify_event(title, str(content))

        async with AsyncSessionLocal() as db:
            event_repo = EventRepository(db)
            entity_repo = EntityRepository(db)
            ee_repo = EventEntityRepository(db)

            existing = await event_repo.get_by_source_url(source_url)
            if existing is not None:
                return None

            event = await event_repo.create({
                "title": title,
                "description": str(content)[:5000],
                "event_type": event_type,
                "severity": "medium",
                "status": "reported",
                "event_date": event_date,
                "source": source,
                "source_url": source_url,
            })

            matched = await self._match_entities(title, str(content), entity_repo)
            for entity_id in matched:
                await ee_repo.create_link(event.id, entity_id)

            await db.commit()

            for entity_id in matched:
                self._dispatch_analysis(event.id, entity_id)

            return {
                "id": event.id,
                "title": event.title,
                "event_type": event.event_type,
                "severity": event.severity,
                "source": event.source,
                "source_url": event.source_url,
                "event_date": event.event_date.isoformat(),
            }

        return None

    async def _match_entities(
        self, title: str, content: str, repo: "EntityRepository",  # noqa: F821
    ) -> list[int]:
        text = (title + " " + content).lower()
        from sqlalchemy import select

        from app.models.entity import Entity as EntityModel

        result = await repo.session.execute(
            select(EntityModel.id, EntityModel.name).where(EntityModel.ticker_symbols.isnot(None))
        )
        matched_ids: list[int] = []
        for row in result.all():
            if row.name.lower() in text:
                matched_ids.append(row.id)
        return matched_ids

    def _dispatch_analysis(self, event_id: int, entity_id: int) -> None:
        from app.workers.analysis_tasks import analyze_event_task
        analyze_event_task.delay(event_id=event_id, entity_ids=[entity_id])
