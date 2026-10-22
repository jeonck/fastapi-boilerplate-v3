"""
Demo API Routes

Small endpoints that make it easy to see each feature in action:

- /demo/cached     Response caching (FastAPI-Cache)
- /demo/limited    Rate limiting, 5 requests / 60 seconds (FastAPI-Limiter)
- /demo/protected  Authentication required (FastAPI Users)
- /demo/cache      Clear the whole cache (superuser only)
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from app.core.limiter import rate_limit
from app.core.users import current_active_user, current_superuser
from app.models.user import User
from app.schemas.base import SuccessResponse

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get("/cached")
@cache(expire=10)
async def cached_endpoint():
    """
    Simulate a slow (1 second) computation whose result is cached for 10 seconds.

    The first call takes ~1s (`X-FastAPI-Cache: MISS`), the next calls are
    served instantly from the cache (`X-FastAPI-Cache: HIT`).
    """
    await asyncio.sleep(1)
    return {
        "message": "This response is cached for 10 seconds",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/limited", dependencies=[Depends(rate_limit(times=5, seconds=60))])
async def limited_endpoint():
    """
    Rate limited endpoint: 5 requests per 60 seconds per client.

    The 6th request within the window returns `429 Too Many Requests`.
    """
    return {
        "message": "Request accepted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/protected")
async def protected_endpoint(user: User = Depends(current_active_user)):
    """Endpoint that requires a valid JWT (`Authorization: Bearer <token>`)."""
    return {"message": f"Hello, {user.email}!", "user_id": str(user.id)}


@router.delete("/cache", response_model=SuccessResponse)
async def clear_cache(user: User = Depends(current_superuser)):
    """Clear every cached response (superuser only)."""
    await FastAPICache.clear()
    return SuccessResponse(message="Cache cleared")
