"""
DJ AI OS — Async Database Connection Layer

PostgreSQL (prod) / SQLite (dev) with SQLAlchemy 2.0 async.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.server.db.models import Base


# ─── Database URL Normalization (asyncpg) ───

# asyncpg.connect() does NOT accept libpq query params like ``sslmode`` or
# ``channel_binding`` — it uses ``ssl``. SQLAlchemy's asyncpg dialect forwards
# every URL query param as a connect() kwarg, so a Neon production URL ending in
# ``?sslmode=require&channel_binding=require`` crashes startup with:
#     TypeError: connect() got an unexpected keyword argument 'sslmode'
# We translate sslmode -> connect_args={"ssl": ...} and drop channel_binding
# (libpq-only; asyncpg has no equivalent). Everything else is preserved.


def _sslmode_to_asyncpg_ssl(mode: str) -> bool:
    """Map a libpq ``sslmode`` value to the asyncpg ``ssl`` connect argument."""
    mode = (mode or "").strip().lower()
    if mode == "require":
        return True
    if mode == "disable":
        return False
    # Fail explicitly rather than silently falling back to asyncpg's default.
    raise ValueError(
        f"Unsupported sslmode={mode!r} in DJ_AI_OS_DATABASE_URL; "
        "asyncpg supports sslmode=require or sslmode=disable."
    )


def _normalize_database_url(url: str) -> tuple[str, dict]:
    """
    Return (clean_url, extra_connect_args) for a database URL.

    Asyncpg URLs only: translate ``sslmode`` into ``connect_args={"ssl": ...}``
    and drop libpq-only ``channel_binding``. All other params are preserved.
    Non-asyncpg URLs (sqlite, psycopg/psycopg2) are returned unchanged.
    """
    if not url.startswith("postgresql+asyncpg://"):
        return url, {}

    parts = urlsplit(url)
    if not parts.query:
        return url, {}

    connect_args: dict = {}
    kept: list[tuple[str, str]] = []
    changed = False
    for key, value in parse_qsl(parts.query):
        if key == "sslmode":
            connect_args["ssl"] = _sslmode_to_asyncpg_ssl(value)
            changed = True
        elif key == "channel_binding":
            changed = True  # libpq-only; asyncpg has no equivalent -> drop
        else:
            kept.append((key, value))

    if not changed:
        return url, {}

    new_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )
    return new_url, connect_args


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
    is_memory_sqlite = url.startswith("sqlite") and ":memory:" in url

    # In-memory SQLite needs StaticPool so all connections share the SAME database.
    # File SQLite uses NullPool; PG uses default pool.
    if is_memory_sqlite:
        poolclass = StaticPool
    elif is_sqlite:
        poolclass = NullPool
    else:
        poolclass = None
    base_connect_args = {"check_same_thread": False} if is_sqlite else {}

    # asyncpg: translate libpq sslmode=... into connect_args={"ssl": ...} so it
    # is never forwarded to asyncpg.connect() as the unsupported `sslmode` kwarg.
    engine_url, ssl_connect_args = _normalize_database_url(url)
    connect_args = {**base_connect_args, **ssl_connect_args}

    _engine = create_async_engine(
        engine_url,
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


async def reset_db() -> None:
    """Reset database engine (for testing). Creates fresh in-memory DB."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None