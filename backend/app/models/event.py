from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.core.enums import EventType, EventSeverity, EventStatus


class Event(Base):
    """
    Represents a geopolitical or market event.

    Events are the core of MarketAtlas - they capture significant occurrences
    that may impact markets (e.g., sanctions, elections, trade agreements).
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Event classification — values constrained by CheckConstraint + StrEnum
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EventStatus.REPORTED)

    # Temporal information
    event_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Source tracking
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships - many-to-many through EventEntity junction table
    event_entities = relationship("EventEntity", back_populates="event", cascade="all, delete-orphan")
    entities = relationship("Entity", secondary="event_entities", back_populates="events", overlaps="event_entities", viewonly=True)
    signals = relationship("Signal", back_populates="event", cascade="all, delete-orphan")

    _event_type_values = ", ".join(f"'{v}'" for v in EventType)
    _severity_values = ", ".join(f"'{v}'" for v in EventSeverity)
    _status_values = ", ".join(f"'{v}'" for v in EventStatus)

    __table_args__ = (
        CheckConstraint(f"event_type IN ({_event_type_values})", name="ck_events_event_type"),
        CheckConstraint(f"severity IN ({_severity_values})", name="ck_events_severity"),
        CheckConstraint(f"status IN ({_status_values})", name="ck_events_status"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_severity", "severity"),
        Index("ix_events_status", "status"),
        Index("ix_events_event_date", "event_date"),
        Index("ix_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title={self.title}, event_type={self.event_type})>"
