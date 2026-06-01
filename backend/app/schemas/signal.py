from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class SignalBase(BaseModel):
    """Base schema for Signal with common fields."""
    
    event_id: int = Field(..., description="ID of the related event")
    entity_id: int = Field(..., description="ID of the related entity")
    signal_type: str = Field(..., description="Signal type: buy, sell, hold, short")
    confidence: Decimal = Field(..., ge=0, le=1, description="Confidence score 0.00-1.00")
    target_price: Optional[Decimal] = Field(None, description="Target price for the signal")
    stop_loss: Optional[Decimal] = Field(None, description="Stop loss price")
    reasoning: str = Field(..., min_length=1, description="Explanation for the signal")
    status: str = Field(default="active", description="Status: active, closed, expired")


class SignalCreate(SignalBase):
    """Schema for creating a new Signal."""
    pass


class SignalUpdate(BaseModel):
    """Schema for updating a Signal."""
    
    signal_type: Optional[str] = None
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    reasoning: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = None
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None
    closed_at: Optional[datetime] = None


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
