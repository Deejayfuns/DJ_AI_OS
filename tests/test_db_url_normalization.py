"""
Regression tests — asyncpg sslmode normalization (P0-1 production blocker).

The production Neon DJ_AI_OS_DATABASE_URL ends in
``?sslmode=require&channel_binding=require``. SQLAlchemy's asyncpg dialect
forwards every URL query param as a kwarg to ``asyncpg.connect()``, which does
NOT accept ``sslmode``/``channel_binding`` (it uses ``ssl``) — crashing startup
with ``TypeError: connect() got an unexpected keyword argument 'sslmode'``.

These tests cover the real production fix and its regression risks.
"""

import asyncio
import os

import pytest

from app.server.db.connection import (
    _normalize_database_url,
    close_db,
    init_engine,
    reset_db,
)


# ─── Exact production Neon URL ───

def test_production_neon_url_normalized():
    """Exact Neon URL: sslmode=require -> ssl=True; channel_binding dropped."""
    url = (
        "postgresql+asyncpg://user:secret@ep-1.us-east-1.aws.neon.tech/db"
        "?sslmode=require&channel_binding=require"
    )
    clean, args = _normalize_database_url(url)
    assert args == {"ssl": True}
    assert "sslmode" not in clean
    assert "channel_binding" not in clean
    assert "user:secret@" in clean  # credentials preserved, never lost


# ─── sslmode mapping ───

def test_sslmode_require_to_ssl_true():
    clean, args = _normalize_database_url(
        "postgresql+asyncpg://u:p@host:5432/db?sslmode=require"
    )
    assert args == {"ssl": True}
    assert clean == "postgresql+asyncpg://u:p@host:5432/db"


def test_sslmode_disable_to_ssl_false():
    _, args = _normalize_database_url(
        "postgresql+asyncpg://u:p@host:5432/db?sslmode=disable"
    )
    assert args == {"ssl": False}


def test_unsupported_sslmode_raises():
    """Unknown/unsupported sslmode fails explicitly — no silent fallback."""
    with pytest.raises(ValueError, match="sslmode"):
        _normalize_database_url(
            "postgresql+asyncpg://u:p@host:5432/db?sslmode=prefer"
        )


# ─── channel_binding drop + preserved params ───

def test_channel_binding_dropped_without_sslmode():
    """channel_binding alone is dropped even with no sslmode to translate."""
    clean, args = _normalize_database_url(
        "postgresql+asyncpg://u:p@host:5432/db?channel_binding=require"
    )
    assert "channel_binding" not in clean
    assert args == {}


def test_other_params_preserved():
    """Non-libpq params are preserved, not silently dropped."""
    clean, args = _normalize_database_url(
        "postgresql+asyncpg://u:p@host:5432/db?command_timeout=30&sslmode=require"
    )
    assert "command_timeout=30" in clean
    assert args == {"ssl": True}


# ─── untouched paths (regression: sqlite + sync PG + plain asyncpg) ───

def test_plain_asyncpg_url_unchanged():
    url = "postgresql+asyncpg://u:p@host:5432/db"
    clean, args = _normalize_database_url(url)
    assert clean == url and args == {}


def test_plain_postgresql_unchanged():
    """Sync psycopg/psycopg2 accept sslmode natively — never touch."""
    url = "postgresql://u:p@host:5432/db?sslmode=require"
    clean, args = _normalize_database_url(url)
    assert clean == url and args == {}


def test_sqlite_unchanged():
    url = "sqlite+aiosqlite:///./db.sqlite"
    clean, args = _normalize_database_url(url)
    assert clean == url and args == {}


# ─── Integration: engine built from production URL must not TypeError ───

def test_production_url_engine_no_typeerror():
    """Engine built from the exact Neon URL no longer forwards sslmode/channel_binding."""
    os.environ["DJ_AI_OS_DATABASE_URL"] = (
        "postgresql+asyncpg://user:secret@ep-1.us-east-1.aws.neon.tech/db"
        "?sslmode=require&channel_binding=require"
    )
    asyncio.run(reset_db())
    engine = init_engine()
    try:
        assert "sslmode" not in str(engine.sync_engine.url)
        assert "channel_binding" not in str(engine.sync_engine.url)
    finally:
        asyncio.run(close_db())
