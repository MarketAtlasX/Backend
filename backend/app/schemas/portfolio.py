from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.portfolio import ALLOCATION_SCHEMA_VERSION


def _alloc_payload(version: int, allocation: dict) -> dict:
    return {"version": version, "allocation": allocation}


class PortfolioCreate(BaseModel):
    """Create a portfolio from a raw sector allocation dict."""

    name: str = Field(..., min_length=1, max_length=100)
    allocation: dict[str, float] = Field(
        ...,
        description="Sector → weight map. Weights need not sum to 1; they are normalized.",
    )

    @field_validator("allocation")
    @classmethod
    def _validate_weights(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("allocation must not be empty")
        for sector, weight in v.items():
            if weight < 0:
                raise ValueError(f"weight for '{sector}' must be >= 0")
        return v


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    allocation: Optional[dict[str, float]] = None


class PortfolioRead(BaseModel):
    id: str
    name: str
    allocation: dict  # {"version": N, "allocation": {...}}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SimulationCreate(BaseModel):
    """Kick off a simulation for a portfolio (scenario described as JSON)."""

    portfolio_id: str = Field(..., description="Portfolio to run against")
    scenario: dict[str, Any] = Field(
        default_factory=dict, description="Scenario payload for the simulator"
    )
    horizons: Optional[list[int]] = None
    monte_carlo_runs: int = Field(default=100, ge=1, le=1000)


class SimulationRead(BaseModel):
    id: str
    portfolio_id: str
    status: str
    scenario: dict
    result: Optional[dict]
    error: Optional[str]
    market_snapshot_time: Optional[datetime]
    sector_data_version: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SectorMetrics(BaseModel):
    """Per-sector return/volatility metrics from the market data feed."""

    return_pct: float
    volatility: float
    computed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class SectorSnapshot(BaseModel):
    """Full sector snapshot injected into the simulator."""

    version: int = ALLOCATION_SCHEMA_VERSION
    sectors: dict[str, SectorMetrics]
    snapshot_time: Optional[datetime] = None


def build_allocation_payload(allocation: dict[str, float]) -> dict:
    return _alloc_payload(ALLOCATION_SCHEMA_VERSION, allocation)
