"""
Create Superuser Script

Creates an administrator account through the FastAPI Users UserManager.

Usage:
    uv run python -m app.scripts.create_superuser admin@example.com 'password'
    ./run.sh createsuperuser admin@example.com 'password'
"""

import asyncio
import contextlib
import sys

from fastapi_users.exceptions import UserAlreadyExists

from app.core.database import create_db_and_tables, get_async_session
from app.core.users import get_user_db, get_user_manager
from app.schemas.user import UserCreate

get_async_session_context = contextlib.asynccontextmanager(get_async_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def create_superuser(email: str, password: str) -> bool:
    """Create a superuser. Returns False if the email is already registered."""
    await create_db_and_tables()
    async with get_async_session_context() as session:
        async with get_user_db_context(session) as user_db:
            async with get_user_manager_context(user_db) as user_manager:
                try:
                    await user_manager.create(
                        UserCreate(
                            email=email,
                            password=password,
                            is_superuser=True,
                            is_verified=True,
                        )
                    )
                except UserAlreadyExists:
                    return False
    return True


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m app.scripts.create_superuser <email> <password>")
        sys.exit(1)

    email, password = sys.argv[1], sys.argv[2]
    if asyncio.run(create_superuser(email, password)):
        print(f"✅ Superuser created: {email}")
    else:
        print(f"❌ User already exists: {email}")
        sys.exit(1)


if __name__ == "__main__":
    main()
