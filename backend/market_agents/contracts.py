"""Shared API and event contracts for MarketAtlas services."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    status: Literal["ok", "degraded"] = "ok"


class MarketSnapshot(BaseModel):
    momentum: float
    volatility: float
    volume: str


class MarketSnapshotRequest(BaseModel):
    prices: List[float] = Field(..., min_length=1)
    volumes: Optional[List[float]] = None


class ImpactRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ImpactResponse(BaseModel):
    local_severity: float
    composite_risk: float
    graph_summary: Dict[str, Dict[str, Any]]
    relations: List[List[str]]


class RecommendationRequest(BaseModel):
    impact: Dict[str, Any]
    market: Dict[str, Any]


class RecommendationResponse(BaseModel):
    action: Literal["BUY", "HOLD", "SELL"]
    reason: str


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    prices: List[float] = Field(..., min_length=1)
    volumes: Optional[List[float]] = None


class AnalysisResponse(BaseModel):
    snapshot: MarketSnapshot
    impact: ImpactResponse
    recommendation: RecommendationResponse


class AgentEvent(BaseModel):
    event_id: str
    event_type: str
    source_service: str
    occurred_at: str
    payload: Dict[str, Any]
