"""
Item Schemas

Pydantic models for the Item resource (used by FastAPI-CrudRouter).
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import BaseSchema


class ItemCreate(BaseSchema):
    """Schema for creating / updating an item."""

    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    price: float = Field(0.0, ge=0, description="Item price")


class Item(ItemCreate):
    """Schema for item response."""

    id: int = Field(..., description="Item ID")
    created_at: Optional[datetime] = Field(None, description="Creation time")


class ItemStats(BaseSchema):
    """Aggregated item statistics (cached)."""

    total_items: int
    total_value: float
    average_price: float
    generated_at: datetime
