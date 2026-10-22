"""
User Model

ORM model used by FastAPI Users. The base table provides
id (UUID), email, hashed_password, is_active, is_superuser and is_verified.
"""

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Application user."""

    __tablename__ = "users"

    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
