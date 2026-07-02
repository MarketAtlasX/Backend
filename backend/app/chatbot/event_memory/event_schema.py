from pydantic import BaseModel, Field


class MarketOutcome(BaseModel):
    sector: str
    impact_pct: float
    volatility: float = 0.0
    recovery_days: int = 0


class HistoricalEvent(BaseModel):
    id: str
    name: str
    description: str
    date: str
    event_type: str
    entities: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    outcomes: list[MarketOutcome] = Field(default_factory=list)
    volatility: float = 0.0
    recovery_days: int = 0
    summary: str = ""


class EventSimilarityResult(BaseModel):
    event: HistoricalEvent
    similarity_score: float
    text_similarity: float = 0.0
    entity_similarity: float = 0.0
    sector_similarity: float = 0.0
    market_similarity: float = 0.0


class SimilarityResponse(BaseModel):
    query: str
    similar_events: list[EventSimilarityResult]
    aggregated_outcomes: dict[str, float]
    confidence: float
