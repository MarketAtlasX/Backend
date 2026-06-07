from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.core.enums import EventType, EventSeverity, EventStatus


def _naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class EventBase(BaseModel):
    """Base schema for Event with common fields."""

    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: str = Field(..., min_length=1, description="Event description")
    event_type: EventType = Field(..., description="Type of event")
    severity: EventSeverity = Field(..., description="Severity level")
    status: EventStatus = Field(default=EventStatus.REPORTED, description="Lifecycle status")
    event_date: datetime = Field(..., description="Date when the event occurred")
    source: Optional[str] = Field(None, max_length=255, description="Source of the event information")
    source_url: Optional[str] = Field(None, max_length=512, description="URL to the source")

    _normalize_event_date = field_validator("event_date")(_naive_utc)


class EventCreate(EventBase):
    """Schema for creating a new Event."""
    pass


class EventUpdate(BaseModel):
    """Schema for updating an Event (all fields optional)."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    event_type: Optional[EventType] = None
    severity: Optional[EventSeverity] = None
    status: Optional[EventStatus] = None
    event_date: Optional[datetime] = None
    source: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=512)

    _normalize_event_date = field_validator("event_date")(_naive_utc)


class EventRead(EventBase):
    """Schema for reading an Event from the database."""

    id: int = Field(description="Event ID")
    created_at: datetime = Field(description="When the event record was created")
    updated_at: datetime = Field(description="When the event record was last updated")

    model_config = {"from_attributes": True}


class EventReadWithEntities(EventRead):
    """Schema for Event with related entities."""

    entities: list["EntityRead"] = Field(default_factory=list, description="Related entities")


# Import EntityRead to avoid circular imports at runtime
from app.schemas.entity import EntityRead  # noqa: E402
