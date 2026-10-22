"""
Rate Limiting (FastAPI-Limiter)

Provides `rate_limit(times, seconds)` which returns a FastAPI dependency.
Requests are counted per client IP + path. When the limit is exceeded the
API responds with `429 Too Many Requests`.

Backend:
- In-memory bucket by default (single process)
- Redis bucket when `REDIS_URL` is configured (shared across workers)
"""

from inspect import isawaitable
from typing import Any, Callable, Dict, List

from fastapi_limiter.depends import RateLimiter as _RateLimiter
from pyrate_limiter import (
    AbstractBucket,
    BucketFactory,
    Duration,
    InMemoryBucket,
    Limiter,
    Rate,
    RateItem,
)
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class RateLimiter(_RateLimiter):
    """
    fastapi-limiter's RateLimiter without the `app.routes` scan.

    The upstream implementation reads `route.path` of every entry in
    `app.routes`, which breaks on newer FastAPI versions where included
    routers appear there. Each dependency owns its own bucket, so the
    client identifier (IP + path) is a sufficient key.
    """

    async def __call__(self, request: Request, response: Response):
        endpoint = request.scope.get("endpoint")
        if getattr(endpoint, "_skip_limiter", False):
            return

        key = await self.identifier(request)
        success = await self.limiter.try_acquire_async(key, blocking=self.blocking)
        if not success:
            return await self.callback(request, response)


class PerKeyBucketFactory(BucketFactory):
    """
    One bucket per client key, so each client gets its own quota.

    (A plain `Limiter(bucket)` shares a single bucket between all keys,
    which would turn the limit into a global one.)
    """

    def __init__(self, rates: List[Rate], namespace: str):
        self.rates = rates
        self.namespace = namespace
        self.buckets: Dict[str, AbstractBucket] = {}
        self.redis = None
        if settings.redis_url:
            from redis import asyncio as aioredis

            self.redis = aioredis.from_url(settings.redis_url)

    async def _redis_bucket(self, key: str) -> AbstractBucket:
        bucket = self.buckets.get(key)
        if bucket is None:
            from pyrate_limiter import RedisBucket

            redis_key = f"rate-limit:{self.namespace}:{key}"
            bucket = await RedisBucket.init(self.rates, self.redis, redis_key)
            self.schedule_leak(bucket)
            self.buckets[key] = bucket
        return bucket

    def _memory_bucket(self, key: str) -> AbstractBucket:
        bucket = self.buckets.get(key)
        if bucket is None:
            bucket = self.create(InMemoryBucket, self.rates)
            self.buckets[key] = bucket
        return bucket

    def wrap_item(self, name: str, weight: int = 1):
        if self.redis is not None:

            async def wrap_async():
                now = (await self._redis_bucket(name)).now()
                if isawaitable(now):
                    now = await now
                return RateItem(name, now, weight=weight)

            return wrap_async()

        return RateItem(name, self._memory_bucket(name).now(), weight=weight)

    def get(self, item: RateItem) -> AbstractBucket:
        # The bucket is always created in wrap_item(), which runs first
        return self.buckets[item.name]


def _build_limiter(times: int, seconds: int) -> Limiter:
    rates = [Rate(times, Duration.SECOND * seconds)]
    return Limiter(PerKeyBucketFactory(rates, namespace=f"{times}/{seconds}s"))


async def _no_limit() -> None:
    """Dependency used when rate limiting is disabled."""


def rate_limit(times: int | None = None, seconds: int | None = None) -> Callable[..., Any]:
    """
    Create a rate limit dependency.

    Usage:
        @router.get("/", dependencies=[Depends(rate_limit(5, 60))])

    - **times**: Allowed number of requests (default: RATE_LIMIT_TIMES)
    - **seconds**: Time window in seconds (default: RATE_LIMIT_SECONDS)
    """
    if not settings.rate_limit_enabled:
        return _no_limit

    times = times or settings.rate_limit_times
    seconds = seconds or settings.rate_limit_seconds
    return RateLimiter(limiter=_build_limiter(times, seconds))
