"""
User Schemas

This module contains Pydantic models used by FastAPI Users.
"""

import uuid
from typing import Optional

from fastapi_users import schemas
from pydantic import Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for user response."""

    full_name: Optional[str] = Field(None, max_length=100, description="Full name")


class UserCreate(schemas.BaseUserCreate):
    """Schema for registering a new user."""

    full_name: Optional[str] = Field(None, max_length=100, description="Full name")


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user information."""

    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
