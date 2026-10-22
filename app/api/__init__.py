"""
API package initialization.

This module initializes the API package and provides
access to all API routers.
"""

from .auth import router as auth_router
from .demo import router as demo_router
from .health import router as health_router
from .items import router as items_router
from .stats import router as stats_router

__all__ = [
    "auth_router",
    "demo_router",
    "health_router",
    "items_router",
    "stats_router",
]
