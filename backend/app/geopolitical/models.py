from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsArticle(BaseModel):
    title: str
    content: str
    source: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str
    sentiment: str
    confidence: float = 0.0


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str
    properties: dict = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0


class MarketSnapshot(BaseModel):
    symbol: str
    momentum: float = 0.0
    volatility: float = 0.0
    volume_status: str = "unknown"


class ImpactResult(BaseModel):
    composite_risk: float = 0.0
    local_severity: float = 0.0
    entity_count: int = 0
    relations: list[tuple[str, str, str]] = []


class SignalResult(BaseModel):
    action: str
    confidence: float
    reason: str


class AnalysisResult(BaseModel):
    news: list[NewsArticle] = []
    entities: list[ExtractedEntity] = []
    graph_nodes: list[GraphNode] = []
    graph_edges: list[GraphEdge] = []
    market: Optional[MarketSnapshot] = None
    impact: Optional[ImpactResult] = None
    signal: Optional[SignalResult] = None
    messages: list[str] = []
