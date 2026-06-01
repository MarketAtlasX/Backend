from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Base schema for Event with common fields."""
    
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: str = Field(..., min_length=1, description="Event description")
    event_type: str = Field(..., description="Type of event (e.g., trade_policy, sanction, election)")
    severity: str = Field(..., description="Severity level: low, medium, high, critical")
    status: str = Field(default="reported", description="Status: reported, confirmed, resolved")
    event_date: datetime = Field(..., description="Date when the event occurred")
    source: Optional[str] = Field(None, max_length=255, description="Source of the event information")
    source_url: Optional[str] = Field(None, max_length=512, description="URL to the source")


class EventCreate(EventBase):
    """Schema for creating a new Event."""
    pass


class EventUpdate(BaseModel):
    """Schema for updating an Event."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    event_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    event_date: Optional[datetime] = None
    source: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=512)


class EventRead(EventBase):
    """Schema for reading an Event from the database."""
    
    id: int = Field(description="Event ID")
    created_at: datetime = Field(description="When the event record was created")
    updated_at: datetime = Field(description="When the event record was last updated")
    
    model_config = {"from_attributes": True}


class EventReadWithEntities(EventRead):
    """Schema for Event with related entities."""
    
    entities: List["EntityRead"] = Field(default_factory=list, description="Related entities")


# Import EntityRead to avoid circular imports at runtime
from app.schemas.entity import EntityRead  # noqa: E402
