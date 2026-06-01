from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class MarketPriceBase(BaseModel):
    """Base schema for MarketPrice with OHLCV data."""
    
    entity_id: int = Field(..., description="ID of the entity (company/ticker)")
    open_price: Decimal = Field(..., description="Opening price")
    high_price: Decimal = Field(..., description="Highest price")
    low_price: Decimal = Field(..., description="Lowest price")
    close_price: Decimal = Field(..., description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    price_date: datetime = Field(..., description="Date of the price data")
    source: str = Field(default="yfinance", description="Source of the price data")


class MarketPriceCreate(MarketPriceBase):
    """Schema for creating a new MarketPrice record."""
    pass


class MarketPriceRead(MarketPriceBase):
    """Schema for reading a MarketPrice record from the database."""
    
    id: int = Field(description="MarketPrice ID")
    created_at: datetime = Field(description="When the record was created")
    updated_at: datetime = Field(description="When the record was last updated")
    
    model_config = {"from_attributes": True}
