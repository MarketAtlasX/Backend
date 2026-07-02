"""Service to ingest geopolitical events from the Knowledge Graph agent.

Calls the external KG agent microservice (port 8005) to fetch live news
articles for entities, creates structured Event records in the database,
and auto-triggers the AI analysis pipeline for each new event.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.entity import EntityRepository
from app.repositories.event import EventRepository
from app.repositories.event_entity import EventEntityRepository
from app.schemas.knowledge_graph import KGResponse
from app.services.kg_service import (
    analyze_country_knowledge_graph,
    analyze_stock_knowledge_graph,
)

logger = logging.getLogger(__name__)

KEYWORD_MAP: dict[str, list[str]] = {
    "sanction": ["sanction", "embargo", "restrict", "ban", "blockade", "asset freeze"],
    "election": ["election", "vote", "ballot", "presidential", "campaign", "poll", "voter"],
    "trade_policy": ["tariff", "trade", "export", "import", "duty", "quota", "trade war", "trade deal"],
    "military_conflict": ["conflict", "war", "attack", "strike", "military", "invasion", "missile", "drone", "bomb", "troop", "rebel"],
    "diplomatic": ["diplomat", "treaty", "summit", "negotiation", "alliance", "pact", "ambassador"],
    "economic_data": ["gdp", "inflation", "unemployment", "rate hike", "rate cut", "gdp growth", "inflation rate"],
    "regulatory": ["regulation", "compliance", "antitrust", "investigation", "fine", "lawsuit", "regulator", "sec"],
    "natural_disaster": ["earthquake", "hurricane", "flood", "wildfire", "pandemic", "drought", "tsunami"],
}


def _classify_event(title: str, content: Optional[str]) -> str:
    text = (title + " " + (content or "")).lower()
    for event_type, keywords in KEYWORD_MAP.items():
        if any(kw in text for kw in keywords):
            return event_type
    return "other"


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            d = datetime.strptime(date_str.replace("Z", "+0000"), fmt)
            return d.replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
    return None


class EventIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._event_repo = EventRepository(session)
        self._entity_repo = EntityRepository(session)
        self._event_entity_repo = EventEntityRepository(session)

    async def ingest_from_ticker(self, entity_id: int, ticker: str) -> int:
        """Call KG agent /analyze, create Event records, link entity, trigger analysis.

        Returns the number of *new* events created (duplicates skipped).
        """
        response = await analyze_stock_knowledge_graph(ticker)
        return await self._process_kg_response(response, entity_id)

    async def ingest_from_country(self, country_name: str, entity_id: int) -> int:
        """Call KG agent /analyze-country, create Event records, link entity.

        Returns the number of *new* events created.
        """
        response = await analyze_country_knowledge_graph(country_name)
        return await self._process_kg_response(response, entity_id)

    async def _process_kg_response(self, response: KGResponse, entity_id: int) -> int:
        created: list[tuple[int, int]] = []

        for article in response.news:
            if not article.title or not article.url:
                continue

            existing = await self._event_repo.get_by_source_url(article.url)
            if existing is not None:
                continue

            event_date = _parse_date(article.date) or datetime.utcnow()
            event_type = _classify_event(article.title, article.content)

            event = await self._event_repo.create({
                "title": article.title[:255],
                "description": (article.content or article.title)[:5000],
                "event_type": event_type,
                "severity": "medium",
                "status": "reported",
                "event_date": event_date,
                "source": (article.source or "knowledge-graph-agent")[:255],
                "source_url": article.url,
            })

            await self._event_entity_repo.create_link(event.id, entity_id)
            created.append((event.id, entity_id))

        await self._session.commit()

        for event_id, ent_id in created:
            self._dispatch_analysis(event_id, ent_id)

        if created:
            self._broadcast_new_events(created)

        return len(created)

    def _broadcast_new_events(self, created: list[tuple[int, int]]) -> None:
        from app.services.event_broadcaster import get_broadcaster

        b = get_broadcaster()
        if b is None:
            return
        for event_id, entity_id in created:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(b.broadcast_event({
                        "id": event_id,
                        "entity_id": entity_id,
                    }))
            except RuntimeError:
                pass

    def _dispatch_analysis(self, event_id: int, entity_id: int) -> None:
        """Fire-and-forget the AI analysis pipeline for a new event.

        Import is deferred to avoid circular dependencies at module level.
        """
        from app.workers.analysis_tasks import analyze_event_task

        analyze_event_task.delay(event_id=event_id, entity_ids=[entity_id])


def get_event_ingestion_service(session: AsyncSession) -> EventIngestionService:
    return EventIngestionService(session)
