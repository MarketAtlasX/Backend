from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.core.enums import SignalType, SignalStatus


def _naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class SignalBase(BaseModel):
    """Base schema for Signal with common fields."""

    event_id: int = Field(..., description="ID of the related event")
    entity_id: int = Field(..., description="ID of the related entity")
    signal_type: SignalType = Field(..., description="Signal direction")
    confidence: Decimal = Field(..., ge=0, le=1, description="Confidence score 0.00-1.00")
    target_price: Optional[Decimal] = Field(None, description="Target price for the signal")
    stop_loss: Optional[Decimal] = Field(None, description="Stop loss price")
    reasoning: str = Field(..., min_length=1, description="Explanation for the signal")
    status: SignalStatus = Field(default=SignalStatus.ACTIVE, description="Lifecycle status")


class SignalCreate(SignalBase):
    """Schema for creating a new Signal."""
    pass


class SignalUpdate(BaseModel):
    """Schema for updating a Signal (all fields optional)."""

    signal_type: Optional[SignalType] = None
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    reasoning: Optional[str] = Field(None, min_length=1)
    status: Optional[SignalStatus] = None
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None
    closed_at: Optional[datetime] = None

    _normalize_closed_at = field_validator("closed_at")(_naive_utc)


class SignalRead(SignalBase):
    """Schema for reading a Signal from the database."""

    id: int = Field(description="Signal ID")
    entry_price: Optional[Decimal] = Field(None, description="Entry price when signal was executed")
    exit_price: Optional[Decimal] = Field(None, description="Exit price when signal was closed")
    pnl_percent: Optional[Decimal] = Field(None, description="Profit/loss percentage")
    created_at: datetime = Field(description="When the signal was created")
    updated_at: datetime = Field(description="When the signal was last updated")
    closed_at: Optional[datetime] = Field(None, description="When the signal was closed")

    model_config = {"from_attributes": True}
