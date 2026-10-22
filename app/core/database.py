"""
Database Configuration

This module sets up SQLAlchemy engines and sessions.

- An async engine/session is used by FastAPI Users.
- A sync engine/session is used by FastAPI-CrudRouter
  (its SQLAlchemyCRUDRouter only supports sync sessions).

Both engines point to the same database.
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


_is_sqlite = settings.database_url.startswith("sqlite")

# Async engine (FastAPI Users)
async_engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

# Sync engine (FastAPI-CrudRouter)
sync_engine = create_engine(
    settings.sync_database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


async def create_db_and_tables() -> None:
    """Create all tables. Use Alembic migrations for production."""
    # Import models so they are registered on Base.metadata
    from app import models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with async_session_maker() as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
