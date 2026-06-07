from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.enums import EntityType


class EntityBase(BaseModel):
    """Base schema for Entity with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Entity name (unique)")
    entity_type: EntityType = Field(..., description="Entity classification")
    description: Optional[str] = Field(None, description="Entity description")
    country_code: Optional[str] = Field(None, max_length=2, description="ISO 3166-1 alpha-2 country code")
    ticker_symbols: Optional[str] = Field(None, max_length=500, description="Comma-separated ticker symbols for companies")


class EntityCreate(EntityBase):
    """Schema for creating a new Entity."""
    pass


class EntityUpdate(BaseModel):
    """Schema for updating an Entity (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    entity_type: Optional[EntityType] = None
    description: Optional[str] = None
    country_code: Optional[str] = Field(None, max_length=2)
    ticker_symbols: Optional[str] = Field(None, max_length=500)


class EntityRead(EntityBase):
    """Schema for reading an Entity from the database."""

    id: int = Field(description="Entity ID")
    created_at: datetime = Field(description="When the entity record was created")
    updated_at: datetime = Field(description="When the entity record was last updated")

    model_config = {"from_attributes": True}
