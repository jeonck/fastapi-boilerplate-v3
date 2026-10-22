"""
Item API Routes (FastAPI-CrudRouter)

Full CRUD endpoints for the Item resource are generated automatically:

- GET    /items           List items (public, paginated)
- GET    /items/{item_id} Get item (public)
- POST   /items           Create item (login required)
- PUT    /items/{item_id} Update item (login required)
- DELETE /items/{item_id} Delete item (login required)
- DELETE /items           Delete all items (superuser only)

Every route is rate limited, and write routes invalidate the "items" cache.
A duplicate name violates the `uq_items_name` constraint -> 409 Conflict.
"""

from typing import AsyncGenerator

from fastapi import Depends
from fastapi_cache import FastAPICache

from app.core.crud import CRUDRouter
from app.core.database import get_db
from app.core.limiter import rate_limit
from app.core.users import current_active_user, current_superuser
from app.models.item import Item as ItemModel
from app.schemas.item import Item, ItemCreate

ITEMS_CACHE_NAMESPACE = "items"


async def invalidate_items_cache() -> AsyncGenerator[None, None]:
    """Clear cached item responses after a write operation."""
    yield
    await FastAPICache.clear(namespace=ITEMS_CACHE_NAMESPACE)


write_dependencies = [Depends(current_active_user), Depends(invalidate_items_cache)]

router = CRUDRouter(
    schema=Item,
    create_schema=ItemCreate,
    update_schema=ItemCreate,
    db_model=ItemModel,
    db=get_db,
    prefix="items",
    tags=["Items"],
    paginate=100,
    dependencies=[Depends(rate_limit())],
    create_route=write_dependencies,
    update_route=write_dependencies,
    delete_one_route=write_dependencies,
    delete_all_route=[Depends(current_superuser), Depends(invalidate_items_cache)],
)
