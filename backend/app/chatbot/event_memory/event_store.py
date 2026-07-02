import re
from difflib import SequenceMatcher
from typing import Optional

from .event_data import HISTORICAL_EVENTS
from .event_schema import EventSimilarityResult, HistoricalEvent, SimilarityResponse

# ruff: noqa: E501

CURRENCY_WORDS = {"dollar", "euro", "pound", "yen", "fiat", "usd", "eur", "gbp", "jpy", "inr", "cny"}


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
        query_lower = query.lower()
        query_entities = self._extract_entities(query_lower)
        query_sectors = sector_filter or self._extract_sectors(query_lower)

        results: list[EventSimilarityResult] = []
        for event in self.events:
            if event_type_filter and event.event_type not in event_type_filter:
                continue
            event_lower = (event.name + " " + event.description + " " + event.summary).lower()
            text_sim = SequenceMatcher(None, query_lower, event_lower).ratio()

            entity_sim = self._entity_overlap(query_entities, set(e.lower() for e in event.entities))
            sector_sim = self._entity_overlap(set(query_sectors), set(s.lower() for s in event.sectors))
            market_sim = self._market_impact_similarity(query_lower, event)

            combined = 0.35 * text_sim + 0.25 * entity_sim + 0.25 * sector_sim + 0.15 * market_sim

            if combined >= min_score:
                results.append(EventSimilarityResult(
                    event=event,
                    similarity_score=round(combined, 4),
                    text_similarity=round(text_sim, 4),
                    entity_similarity=round(entity_sim, 4),
                    sector_similarity=round(sector_sim, 4),
                    market_similarity=round(market_sim, 4),
                ))

        results.sort(key=lambda r: r.similarity_score, reverse=True)
        results = results[:top_k]

        aggregated: dict[str, float] = {}
        if results:
            for r in results:
                for o in r.event.outcomes:
                    sector = o.sector
                    weighted = o.impact_pct * r.similarity_score
                    aggregated[sector] = aggregated.get(sector, 0) + weighted

        confidence = max((r.similarity_score for r in results), default=0.0)

        return SimilarityResponse(
            query=query,
            similar_events=results,
            aggregated_outcomes=aggregated,
            confidence=round(confidence, 4),
        )

    def add_event(self, event: HistoricalEvent) -> None:
        existing_ids = {e.id for e in self.events}
        if event.id not in existing_ids:
            self.events.append(event)

    def get_event_by_id(self, event_id: str) -> Optional[HistoricalEvent]:
        for e in self.events:
            if e.id == event_id:
                return e
        return None

    def _extract_entities(self, text: str) -> set[str]:
        words = re.findall(r"[a-z]+", text)
        entities = {w for w in words if len(w) > 2}
        return entities - CURRENCY_WORDS

    def _extract_sectors(self, text: str) -> set[str]:
        sector_keywords = {
            "tech", "technology", "financial", "bank", "energy", "oil", "gas",
            "health", "healthcare", "pharma", "manufacturing", "industrial",
            "defense", "military", "agriculture", "farm", "transport", "airline",
            "shipping", "logistics", "insurance", "real estate", "retail",
            "semiconductor", "chip", "telecom", "media", "utility",
        }
        words = set(re.findall(r"[a-z]+", text.lower()))
        return words & sector_keywords

    def _entity_overlap(self, query_set: set[str], event_set: set[str]) -> float:
        if not query_set:
            return 0.0
        intersection = query_set & event_set
        return len(intersection) / len(query_set) if query_set else 0.0

    def _market_impact_similarity(self, query: str, event: HistoricalEvent) -> float:
        impact_words = {"crash", "surge", "rally", "plunge", "soar", "drop", "rise", "fall", "decline", "boom", "bust"}
        query_words = set(re.findall(r"[a-z]+", query.lower()))
        impact_overlap = query_words & impact_words
        if not impact_overlap:
            return 0.0
        return min(1.0, len(impact_overlap) * 0.2)


event_store = EventStore()


def find_similar_events(
    query: str,
    top_k: int = 5,
    min_score: float = 0.1,
    sector_filter: Optional[list[str]] = None,
    event_type_filter: Optional[list[str]] = None,
) -> SimilarityResponse:
    return event_store.find_similar(query, top_k, min_score, sector_filter, event_type_filter)
