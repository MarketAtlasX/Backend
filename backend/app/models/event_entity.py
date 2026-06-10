from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventEntity(Base):
    """
    Junction table for many-to-many relationship between Events and Entities.
    
    Allows an entity (company, country, etc.) to be mentioned in multiple events,
    and an event to involve multiple entities.
    """

    __tablename__ = "event_entities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    event = relationship("Event", back_populates="event_entities", overlaps="entities")
    entity = relationship("Entity", back_populates="event_entities", overlaps="events")

    # Indexes and constraints
    __table_args__ = (
        Index("ix_event_entities_event_id", "event_id"),
        Index("ix_event_entities_entity_id", "entity_id"),
    )

    def __repr__(self) -> str:
        return f"<EventEntity(event_id={self.event_id}, entity_id={self.entity_id})>"
