from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class IntentType(str, Enum):
    NEWS = "NEWS"
    MARKET = "MARKET"
    IMPACT = "IMPACT"
    RECOMMENDATION = "RECOMMENDATION"
    SIMULATION = "SIMULATION"
    GRAPH = "GRAPH"
    REPORT = "REPORT"


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
