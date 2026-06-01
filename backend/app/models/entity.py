from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Entity(Base):
    """
    Represents a geopolitical entity affected by or mentioned in an event.
    
    Entities can be countries, regions, companies, or individuals that are
    relevant to events and market movements.
    """

    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # country, company, person, region
    
    # Additional metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    ticker_symbols: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # CSV list for companies
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    event = relationship("Event", back_populates="entities")
    signals = relationship("Signal", back_populates="entity", cascade="all, delete-orphan")
    market_prices = relationship("MarketPrice", back_populates="entity", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_entities_entity_type", "entity_type"),
        Index("ix_entities_country_code", "country_code"),
        Index("ix_entities_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, name={self.name}, entity_type={self.entity_type})>"
