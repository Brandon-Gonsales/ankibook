import logging
from typing import Any
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Engine configuration
connect_args: dict[str, Any] = {}
if "asyncpg" in settings.async_database_url:
    # Required for Supabase connection pooler (port 6543 / PgBouncer / Supavisor)
    connect_args["statement_cache_size"] = 0
elif "psycopg" in settings.async_database_url:
    # Same for psycopg: the transaction pooler (port 6543) can't keep
    # prepared statements, so never prepare them.
    connect_args["prepare_threshold"] = None

engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for yielding an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> dict[str, str | bool]:
    """Quickly check database connectivity for the health check endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "connected", "healthy": True}
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        result: dict[str, str | bool] = {"status": "disconnected", "healthy": False}
        # Connection errors can reveal hosts and user names: only show them locally.
        if settings.is_development:
            result["error"] = str(exc)
        return result


async def init_db() -> None:
    """Create tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
