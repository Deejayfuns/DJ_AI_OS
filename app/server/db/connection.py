"""
DJ AI OS — Async Database Connection Layer

PostgreSQL (prod) / SQLite (dev) with SQLAlchemy 2.0 async.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.server.db.models import Base


# ─── Engine & Session Factory ───

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    """
    Resolve database URL from env.
    Prod: DJ_AI_OS_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
    Dev:  defaults to sqlite+aiosqlite:///./dj_ai_os_dev.db
    """
    url = os.environ.get("DJ_AI_OS_DATABASE_URL", "").strip()
    if url:
        return url
    # Default: local SQLite file in project root (dev only)
    return "sqlite+aiosqlite:///./dj_ai_os_dev.db"


def init_engine() -> AsyncEngine:
    """Create and cache the async engine."""
    global _engine
    if _engine is not None:
        return _engine

    url = get_database_url()
    is_sqlite = url.startswith("sqlite")

    # SQLite needs NullPool; PG can use default pool
    poolclass = NullPool if is_sqlite else None
    connect_args = {"check_same_thread": False} if is_sqlite else {}

    _engine = create_async_engine(
        url,
        poolclass=poolclass,
        connect_args=connect_args,
        echo=os.environ.get("DJ_AI_OS_DB_ECHO", "").lower() in ("1", "true", "yes"),
        future=True,
    )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = init_engine()
    _session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields an AsyncSession.
    Usage: async def endpoint(session: AsyncSession = Depends(get_db_session)):
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables (dev only — prod uses Alembic migrations)."""
    engine = init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose engine on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None