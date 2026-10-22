"""
Core package initialization.

This module initializes the core package and provides common utilities
for the FastAPI application.
"""

from .config import settings, get_settings

__all__ = ["settings", "get_settings"]
