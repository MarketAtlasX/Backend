from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class IntentType(str, Enum):
    NEWS = "NEWS"
    MARKET = "MARKET"
    IMPACT = "IMPACT"
    RECOMMENDATION = "RECOMMENDATION"
    SIMULATION = "SIMULATION"
    GRAPH = "GRAPH"
    REPORT = "REPORT"
    SIMILARITY = "SIMILARITY"
    RISK = "RISK"


class RiskRating(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class RiskFactor(BaseModel):
    name: str
    value: float
    weight: float
    score: float
    direction: str


class RiskIndex(BaseModel):
    ticker: str
    company_name: str = ""
    overall_score: float
    rating: RiskRating
    factors: list[RiskFactor] = []
    benchmark: dict[str, Any] = {}
    summary: str = ""
    timestamp: str = ""


class RiskIndexRequest(BaseModel):
    ticker: str
    benchmark: str = "SPY"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    query: str
    response: str
    intent: IntentType
    agents_used: list[str]
    confidence: float
    sources: list[str] = []
    report: Optional[dict[str, Any]] = None
    explanations: Optional[dict[str, Any]] = None


class GraphEntity(BaseModel):
    name: str
    type: str
    properties: dict[str, Any] = {}


class GraphRelation(BaseModel):
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = {}


class IntelligenceReport(BaseModel):
    title: str
    event: str
    affected_sectors: list[str]
    risk_score: float
    expected_market_impact: str
    recommended_assets: list[str]
    confidence: float
    reasoning: str
    sources: list[str] = []
    timestamp: str = ""


class SimulationResult(BaseModel):
    scenario: str
    consequences: dict[str, str]
    probability: float
    time_horizon: str
    key_risks: list[str]


class SimilarityRequest(BaseModel):
    query: str
    top_k: int = 5
    min_score: float = 0.1
    sector_filter: Optional[list[str]] = None
    event_type_filter: Optional[list[str]] = None


class MarketIntelligenceRequest(BaseModel):
    ticker: str
    include_profile: bool = True
    include_news: bool = True
    days: int = 30


class CountryBriefRequest(BaseModel):
    country: str
    include_tickers: bool = True
    days: int = 30
