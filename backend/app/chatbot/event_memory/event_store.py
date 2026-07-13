import asyncio
from typing import Optional

from ..pipeline_adapter import run_similarity_pipeline
from .event_data import HISTORICAL_EVENTS
from .event_schema import EventSimilarityResult, HistoricalEvent, SimilarityResponse


class EventStore:
    def __init__(self) -> None:
        self.events: list[HistoricalEvent] = list(HISTORICAL_EVENTS)

    def find_similar(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.1,
        sector_filter: Optional[list[str]] = None,
        event_type_filter: Optional[list[str]] = None,
    ) -> SimilarityResponse:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio  # type: ignore[import-untyped]
                nest_asyncio.apply()
                result = loop.run_until_complete(
                    run_similarity_pipeline(query=query, content=query, top_k=top_k)
                )
            else:
                result = asyncio.run(
                    run_similarity_pipeline(query=query, content=query, top_k=top_k)
                )
        except Exception:
            result = {"similar_events": [], "aggregated_outcomes": {}}

        raw_events = result.get("similar_events", [])
        aggregated = result.get("aggregated_outcomes", {})

        similar_events = []
        for raw in raw_events:
            title = raw.get("title", raw.get("matched_event_id", "Unknown"))
            score = raw.get("similarity_score", raw.get("score", 0))
            score = float(score) if score else 0.0
            payload = raw.get("payload", {})
            matched_id = raw.get("matched_event_id", raw.get("id", ""))

            event = self._find_event_by_id_or_title(matched_id, title)
            if event is None:
                event = HistoricalEvent(
                    id=matched_id,
                    name=title,
                    year=0,
                    description=payload.get("description", ""),
                    summary=payload.get("summary", ""),
                    event_type=payload.get("event_type", "unknown"),
                    sectors=payload.get("sectors", []),
                    entities=payload.get("entities", []),
                    outcomes=[],
                    market_impact=payload.get("market_impact", 0),
                    source=payload.get("source", "Pipeline"),
                )

            similar_events.append(EventSimilarityResult(
                event=event,
                similarity_score=round(score, 4),
                text_similarity=round(score, 4),
                entity_similarity=0,
                sector_similarity=0,
                market_similarity=0,
            ))

        similar_events.sort(key=lambda r: r.similarity_score, reverse=True)
        similar_events = similar_events[:top_k]

        if not similar_events:
            similar_events, aggregated = self._fallback_query(query, top_k, sector_filter, event_type_filter)

        confidence = max((r.similarity_score for r in similar_events), default=0.0)

        return SimilarityResponse(
            query=query,
            similar_events=similar_events,
            aggregated_outcomes=aggregated,
            confidence=round(confidence, 4),
        )

    def _find_event_by_id_or_title(self, event_id: str, title: str) -> HistoricalEvent | None:
        tid = event_id.lower().replace(" ", "_")
        for e in self.events:
            if e.id == tid or e.name.lower() == title.lower():
                return e
        return None

    def _fallback_query(
        self,
        query: str,
        top_k: int,
        sector_filter: Optional[list[str]],
        event_type_filter: Optional[list[str]],
    ) -> tuple[list[EventSimilarityResult], dict[str, float]]:
        from difflib import SequenceMatcher
        import re

        query_lower = query.lower()
        results = []
        for event in self.events:
            if event_type_filter and event.event_type not in event_type_filter:
                continue
            text = (event.name + " " + event.description + " " + event.summary).lower()
            text_sim = SequenceMatcher(None, query_lower, text).ratio()
            if text_sim >= 0.05:
                results.append(EventSimilarityResult(
                    event=event,
                    similarity_score=round(text_sim, 4),
                    text_similarity=round(text_sim, 4),
                    entity_similarity=0,
                    sector_similarity=0,
                    market_similarity=0,
                ))

        results.sort(key=lambda r: r.similarity_score, reverse=True)
        results = results[:top_k]

        aggregated = {}
        for r in results:
            for o in r.event.outcomes:
                weighted = o.impact_pct * r.similarity_score
                aggregated[o.sector] = aggregated.get(o.sector, 0) + weighted

        return results, aggregated

    def add_event(self, event: HistoricalEvent) -> None:
        existing_ids = {e.id for e in self.events}
        if event.id not in existing_ids:
            self.events.append(event)

    def get_event_by_id(self, event_id: str) -> Optional[HistoricalEvent]:
        for e in self.events:
            if e.id == event_id:
                return e
        return None


event_store = EventStore()


def find_similar_events(
    query: str,
    top_k: int = 5,
    min_score: float = 0.1,
    sector_filter: Optional[list[str]] = None,
    event_type_filter: Optional[list[str]] = None,
) -> SimilarityResponse:
    return event_store.find_similar(query, top_k, min_score, sector_filter, event_type_filter)
