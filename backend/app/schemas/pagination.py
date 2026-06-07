from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


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


@dataclass
class Page(Generic[T]):
    """
    Internal service return type for paginated result sets.

    Services return Page[T] instead of raw tuples so callers have
    named attributes rather than positional unpacking.
    """

    items: list[T]
    total: int
    skip: int
    limit: int

    def to_dict(self, serializer=None) -> dict:
        """
        Convert to PaginatedResponse-compatible dict.

        If *serializer* is provided (a Pydantic model class), each ORM
        item is converted via ``serializer.model_validate(item)`` so the
        resulting dict is JSON-serialisable and suitable for use with
        ``response_model=PaginatedResponse``.
        """
        items = (
            [serializer.model_validate(item) for item in self.items]
            if serializer
            else self.items
        )
        return {
            "total": self.total,
            "skip": self.skip,
            "limit": self.limit,
            "items": items,
        }
