import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    AlertType,
    ImpactDirection,
    ImpactType,
    LiveEventStatus,
    PriceDirection,
    TimeHorizon,
)
from app.database import Base


class LiveEvent(Base):
    __tablename__ = "live_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sub_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=LiveEventStatus.BREAKING)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_urls: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    detected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    extra_meta: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    impacts = relationship("EventImpact", back_populates="event", cascade="all, delete-orphan")
    news_articles = relationship("EventNewsArticle", back_populates="event", cascade="all, delete-orphan")
    alerts = relationship("EventAlert", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("severity >= 0.0 AND severity <= 10.0", name="ck_live_events_severity"),
        CheckConstraint("impact_score IS NULL OR (impact_score >= 0.0 AND impact_score <= 1.0)", name="ck_live_events_impact"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)", name="ck_live_events_confidence"),
        Index("ix_live_events_status_first_seen", "status", "first_seen_at"),
        Index("ix_live_events_event_type", "event_type"),
        Index("ix_live_events_severity", "severity"),
        Index("ix_live_events_country_code", "country_code"),
        Index("ix_live_events_source", "source"),
        Index("ix_live_events_first_seen_at", "first_seen_at"),
    )

    def __repr__(self) -> str:
        return f"<LiveEvent(id={self.id}, title={self.title}, type={self.event_type})>"


class EventImpact(Base):
    __tablename__ = "event_impacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("live_events.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("entities.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    impact_direction: Mapped[str] = mapped_column(String(20), nullable=False, default=ImpactDirection.NEUTRAL)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    impact_type: Mapped[str] = mapped_column(String(50), nullable=False, default=ImpactType.PRICE)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning_factors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False, default="ai_service")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("LiveEvent", back_populates="impacts")
    affected_assets = relationship("EventAffectedAsset", back_populates="impact", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("impact_score >= 0.0 AND impact_score <= 1.0", name="ck_event_impacts_score"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_event_impacts_confidence"),
    )

    def __repr__(self) -> str:
        return f"<EventImpact(event={self.event_id}, entity={self.entity_name}, score={self.impact_score})>"


class EventAffectedAsset(Base):
    __tablename__ = "event_affected_assets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    impact_id: Mapped[str] = mapped_column(ForeignKey("event_impacts.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_move: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_impact: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_horizon: Mapped[str] = mapped_column(String(20), nullable=False, default=TimeHorizon.SHORT_TERM)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_direction: Mapped[str] = mapped_column(String(10), nullable=False, default=PriceDirection.MIXED)

    impact = relationship("EventImpact", back_populates="affected_assets")

    __table_args__ = (
        Index("ix_event_affected_assets_ticker", "ticker"),
        Index("ix_event_affected_assets_asset_type", "asset_type"),
    )

    def __repr__(self) -> str:
        return f"<EventAffectedAsset(name={self.name}, type={self.asset_type})>"


class EventNewsArticle(Base):
    __tablename__ = "event_news_articles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("live_events.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    content_snippet: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("LiveEvent", back_populates="news_articles")

    __table_args__ = (
        UniqueConstraint("url", name="uq_event_news_article_url"),
        Index("ix_event_news_articles_source", "source"),
        Index("ix_event_news_articles_relevance", "event_id", "relevance_score"),
    )

    def __repr__(self) -> str:
        return f"<EventNewsArticle(title={self.title}, source={self.source})>"


class EventAlert(Base):
    __tablename__ = "event_alerts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_id: Mapped[Optional[str]] = mapped_column(ForeignKey("live_events.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False, default=AlertType.IN_APP)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("LiveEvent", back_populates="alerts")

    __table_args__ = (
        Index("ix_event_alerts_user_read", "user_id", "is_read"),
    )

    def __repr__(self) -> str:
        return f"<EventAlert(id={self.id}, title={self.title})>"


class UserEventFilter(Base):
    __tablename__ = "user_event_filters"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    filter_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_user_event_filters_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<UserEventFilter(name={self.name}, user={self.user_id})>"
