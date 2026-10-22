"""
Statistics API Routes (FastAPI-Cache)

Aggregation queries are a typical caching target: the result is cached
for 60 seconds and invalidated whenever an item is created/updated/deleted.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.items import ITEMS_CACHE_NAMESPACE
from app.core.database import get_async_session
from app.core.limiter import rate_limit
from app.models.item import Item as ItemModel
from app.schemas.item import ItemStats

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "/items",
    response_model=ItemStats,
    dependencies=[Depends(rate_limit())],
)
@cache(expire=60, namespace=ITEMS_CACHE_NAMESPACE)
async def item_stats(session: AsyncSession = Depends(get_async_session)):
    """
    Get aggregated item statistics.

    The response is cached (check the `X-FastAPI-Cache: HIT/MISS` header).
    """
    result = await session.execute(
        select(
            func.count(ItemModel.id),
            func.coalesce(func.sum(ItemModel.price), 0.0),
            func.coalesce(func.avg(ItemModel.price), 0.0),
        )
    )
    total, total_value, average = result.one()
    return ItemStats(
        total_items=total,
        total_value=round(float(total_value), 2),
        average_price=round(float(average), 2),
        generated_at=datetime.now(timezone.utc),
    )
