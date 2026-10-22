"""
Application Configuration Settings

This module handles all configuration settings for the FastAPI application,
including environment variables, database, authentication, rate limiting
and caching options.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from sqlalchemy.engine import make_url


# Async driver -> sync driver mapping (FastAPI-CrudRouter uses a sync Session)
_SYNC_DRIVERS = {
    "sqlite+aiosqlite": "sqlite",
    "postgresql+asyncpg": "postgresql+psycopg",
    "mysql+aiomysql": "mysql+pymysql",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Information
    app_name: str = "FastAPI Boilerplate v3"
    app_version: str = "0.1.0"
    app_description: str = (
        "FastAPI boilerplate with FastAPI Users, CrudRouter, Limiter and Cache"
    )

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    environment: str = "development"

    # CORS Configuration
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]

    # Logging Configuration
    log_level: str = "INFO"

    # Database Configuration (async URL; sync URL is derived for CrudRouter)
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Security Configuration (FastAPI Users)
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-please-use-a-long-random-string"
    access_token_expire_minutes: int = 30

    # Redis Configuration (Optional - in-memory backends are used when unset)
    redis_url: Optional[str] = None

    # Rate Limiting Configuration (FastAPI-Limiter)
    rate_limit_enabled: bool = True
    rate_limit_times: int = 60
    rate_limit_seconds: int = 60
    auth_rate_limit_times: int = 10  # login/register brute-force protection
    auth_rate_limit_seconds: int = 60

    # Cache Configuration (FastAPI-Cache)
    cache_enabled: bool = True
    cache_prefix: str = "fastapi-cache"
    cache_expire_seconds: int = 60

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith('['):
            return [origin.strip() for origin in v.split(',')]
        return v

    @field_validator('allowed_methods', mode='before')
    @classmethod
    def parse_cors_methods(cls, v):
        if isinstance(v, str) and not v.startswith('['):
            return [method.strip() for method in v.split(',')]
        return v

    @field_validator('allowed_headers', mode='before')
    @classmethod
    def parse_cors_headers(cls, v):
        if isinstance(v, str) and not v.startswith('['):
            return [header.strip() for header in v.split(',')]
        return v

    @property
    def sync_database_url(self) -> str:
        """Sync version of `database_url` for FastAPI-CrudRouter."""
        url = make_url(self.database_url)
        driver = _SYNC_DRIVERS.get(url.drivername, url.drivername)
        return url.set(drivername=driver).render_as_string(hide_password=False)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
