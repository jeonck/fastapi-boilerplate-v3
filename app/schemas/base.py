"""
Base Schemas

This module contains base Pydantic models and common schemas
used throughout the application.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    """Base schema with common fields."""

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "validate_assignment": True
    }


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthCheckResponse(BaseSchema):
    """Health check response schema."""

    status: str = Field(..., description="Application status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Current environment")


class ErrorResponse(BaseSchema):
    """Standard error response schema."""

    error: bool = True
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SuccessResponse(BaseSchema):
    """Standard success response schema."""

    success: bool = True
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
