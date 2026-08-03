import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ALLOCATION_SCHEMA_VERSION = 1


class Portfolio(Base):
    """A user-owned portfolio definition (allocation only — results live in SimulationRun)."""

    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Versioned allocation payload: {"version": 1, "allocation": {sector: weight}}
    allocation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    runs = relationship("SimulationRun", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_portfolios_user_created", "user_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, user={self.user_id}, name={self.name})>"


class SimulationRun(Base):
    """A single simulation run against a portfolio, with market snapshot provenance."""

    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Market snapshot provenance — lets reruns be compared/reproduced.
    market_snapshot_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sector_data_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    portfolio = relationship("Portfolio", back_populates="runs")

    __table_args__ = (Index("ix_simulation_runs_portfolio_created", "portfolio_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<SimulationRun(id={self.id}, portfolio={self.portfolio_id}, status={self.status})>"


class SectorCache(Base):
    """Cached per-sector return/volatility metrics with an expiry window."""

    __tablename__ = "sector_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    return_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    volatility: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<SectorCache(sector={self.sector}, volatility={self.volatility})>"
