"""
Health Check API Routes

This module contains health check and system status endpoints.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings
from app.schemas.base import HealthCheckResponse, SuccessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthCheckResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint.

    Returns the current status and basic information about the application.
    """
    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ping", response_model=SuccessResponse)
async def ping():
    """
    Simple ping endpoint for basic connectivity testing.
    """
    return SuccessResponse(
        message="pong",
        data={"timestamp": datetime.now(timezone.utc).isoformat()}
    )


@router.get("/info", response_model=dict)
async def app_info(settings: Settings = Depends(get_settings)):
    """
    Application information endpoint.

    Returns detailed information about the application configuration.
    """
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "environment": settings.environment,
        "debug": settings.debug,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
