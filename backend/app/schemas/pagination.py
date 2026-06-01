from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of records to return")


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    
    total: int = Field(description="Total number of records available")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Number of records returned")
    items: list = Field(description="List of items in this page")
