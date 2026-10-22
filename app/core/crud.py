"""
CRUD Router (FastAPI-CrudRouter)

`SQLAlchemyCRUDRouter` catches `IntegrityError` itself and answers 422 -
on update it even returns the raw database error message. This subclass
lets constraint violations reach the global handler in app/core/errors.py,
so every endpoint answers the same way: `409 Conflict`.

Import `CRUDRouter` from here instead of `fastapi_crudrouter`.
"""

from typing import Any

import app.core.crudrouter_compat  # noqa: F401  (must be imported before CrudRouter)
from fastapi import Depends
from fastapi_crudrouter import SQLAlchemyCRUDRouter
from sqlalchemy.orm import Session

__all__ = ["CRUDRouter"]


class CRUDRouter(SQLAlchemyCRUDRouter):
    """SQLAlchemyCRUDRouter that propagates IntegrityError (-> 409)."""

    def _create(self, *args: Any, **kwargs: Any):
        def route(
            model: self.create_schema,  # type: ignore
            db: Session = Depends(self.db_func),
        ):
            db_model = self.db_model(**model.model_dump())
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            return db_model

        return route

    def _update(self, *args: Any, **kwargs: Any):
        def route(
            item_id: self._pk_type,  # type: ignore
            model: self.update_schema,  # type: ignore
            db: Session = Depends(self.db_func),
        ):
            db_model = self._get_one()(item_id, db)
            for key, value in model.model_dump(exclude={self._pk}).items():
                if hasattr(db_model, key):
                    setattr(db_model, key, value)
            db.commit()
            db.refresh(db_model)
            return db_model

        return route
