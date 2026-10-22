"""
Response Caching (FastAPI-Cache)

Initializes FastAPI-Cache at application startup.

Backend:
- In-memory backend by default (single process)
- Redis backend when `REDIS_URL` is configured (shared across workers)

Usage:
    from fastapi_cache.decorator import cache

    @router.get("/")
    @cache(expire=60, namespace="items")
    async def endpoint(): ...

    await FastAPICache.clear(namespace="items")  # invalidate

Cache keys are built from the HTTP method, path and query string
(see `request_key_builder`), so endpoints with DB-session dependencies
are cached correctly. Do NOT cache per-user responses with this key
builder - pass a custom `key_builder` that includes the user instead.
"""

import hashlib
import logging
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)


def request_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a cache key from the endpoint and request URL (ignores dependencies)."""
    url = f"{request.method}:{request.url.path}?{request.url.query}" if request else ""
    raw = f"{func.__module__}:{func.__name__}:{url}"
    return f"{namespace}:{hashlib.md5(raw.encode()).hexdigest()}"


def init_cache() -> None:
    """Initialize FastAPI-Cache with the configured backend."""
    if settings.redis_url:
        from redis import asyncio as aioredis
        from fastapi_cache.backends.redis import RedisBackend

        redis = aioredis.from_url(settings.redis_url)
        backend = RedisBackend(redis)
        logger.info("Cache backend: Redis")
    else:
        backend = InMemoryBackend()
        logger.info("Cache backend: in-memory")

    FastAPICache.init(
        backend,
        prefix=settings.cache_prefix,
        expire=settings.cache_expire_seconds,
        key_builder=request_key_builder,
        enable=settings.cache_enabled,
    )
