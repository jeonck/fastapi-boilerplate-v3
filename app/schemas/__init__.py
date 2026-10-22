"""
Schemas package initialization.

This module initializes the schemas package and provides
access to all Pydantic models used in the application.
"""

from .base import (
    BaseSchema,
    TimestampMixin,
    HealthCheckResponse,
    ErrorResponse,
    SuccessResponse,
)
from .item import Item, ItemCreate, ItemStats
from .user import UserCreate, UserRead, UserUpdate

__all__ = [
    # Base schemas
    "BaseSchema",
    "TimestampMixin",
    "HealthCheckResponse",
    "ErrorResponse",
    "SuccessResponse",
    # User schemas
    "UserRead",
    "UserCreate",
    "UserUpdate",
    # Item schemas
    "Item",
    "ItemCreate",
    "ItemStats",
]
