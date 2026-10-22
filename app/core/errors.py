"""
Database Error Handling

Business rules that must hold under concurrency (uniqueness, no overlapping
bookings, non-negative balances, ...) belong in the database as constraints.
A Python check like `if await exists(...): raise HTTPException(...)` is a
race: two concurrent requests can both pass the check and both insert.

With the rule in the database, the losing request fails with an
`IntegrityError`. This handler turns it into a clean `409 Conflict`
instead of a `500`, without leaking SQL or constraint details to clients.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Translate a database constraint violation into 409 Conflict."""
    logger.info(f"Constraint violation on {request.method} {request.url.path}: {exc.orig}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "The request conflicts with existing data."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register database-related exception handlers on the app."""
    app.add_exception_handler(IntegrityError, integrity_error_handler)
