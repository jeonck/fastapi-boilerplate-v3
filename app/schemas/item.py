"""
Item Schemas

Pydantic models for the Item resource (used by FastAPI-CrudRouter).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from .base import BaseSchema


class ItemCreate(BaseSchema):
    """Schema for creating / updating an item."""

    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    price: Decimal = Field(
        Decimal("0"),
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="Item price (exact decimal, serialized as a string)",
    )


class Item(ItemCreate):
    """Schema for item response."""

    id: int = Field(..., description="Item ID")
    created_at: Optional[datetime] = Field(None, description="Creation time")


class ItemStats(BaseSchema):
    """Aggregated item statistics (cached)."""

    total_items: int
    total_value: Decimal
    average_price: Decimal
    generated_at: datetime
