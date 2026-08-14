"""
P0-4 PostgreSQL Migration Verification Test

Verifies `alembic upgrade head` against a real PostgreSQL instance:
1. Migration chain is valid (single head)
2. Upgrade creates all 7 tables with correct schema
3. Schema matches SQLAlchemy models (Base.metadata)
4. Downgrade drops all domain tables
5. Re-upgrade is idempotent

Skip if PostgreSQL is not reachable (CI can enable via DJ_AI_OS_DATABASE_URL).
"""
import os
import pytest

# Only run if a PostgreSQL URL is configured
PG_URL = os.environ.get("DJ_AI_OS_DATABASE_URL", "")
if not PG_URL.startswith("postgresql"):
    pytest.skip(
        "PostgreSQL not configured (set DJ_AI_OS_DATABASE_URL=postgresql+asyncpg://...)",
        allow_module_level=True,
    )

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.server.db.models import Base


ALEMBIC_INI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "alembic.ini",
)


def _alembic_config():
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("script_location", "app/server/db/migrations")
    cfg.set_main_option("sqlalchemy.url", PG_URL)
    cfg.set_main_option("prepend_sys_path", ".")
    # Avoid fileConfig() lookup of missing logging config in env.py by faking cfg name
    cfg.config_file_name = ALEMBIC_INI
    return cfg


def _table_names(engine):
    with engine.connect() as conn:
        return inspect(engine).get_table_names()


def test_alembic_heads_single():
    """Migration chain has exactly one head."""
    cfg = _alembic_config()
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert heads == ["0001_initial"], f"Expected single head, got: {heads}"


def test_alembic_upgrade_head_creates_all_tables():
    """alembic upgrade head creates all 7 expected tables."""
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    from sqlalchemy import create_engine
    engine = create_engine(PG_URL.replace("+asyncpg", ""), future=True)
    try:
        tables = _table_names(engine)
        expected = {
            "users",
            "licenses",
            "machine_activations",
            "subscriptions",
            "webhook_events",
            "audit_log",
            "alembic_version",
        }
        assert expected.issubset(set(tables)), f"Missing tables: {expected - set(tables)}"
    finally:
        engine.dispose()


def test_schema_matches_models():
    """Migration schema matches SQLAlchemy Base.metadata tables."""
    from sqlalchemy import create_engine
    engine = create_engine(PG_URL.replace("+asyncpg", ""), future=True)
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            migrated_tables = set(inspector.get_table_names())

            # Exclude alembic_version (not a model)
            model_tables = {t.name for t in Base.metadata.sorted_tables}
            assert model_tables.issubset(migrated_tables), (
                f"Model tables missing from migration: {model_tables - migrated_tables}"
            )

            # Verify column counts match for each model table
            for table in Base.metadata.sorted_tables:
                migrated_cols = {
                    c["name"] for c in inspector.get_columns(table.name)
                }
                model_cols = {c.name for c in table.columns}
                assert migrated_cols == model_cols, (
                    f"Column mismatch in {table.name}: "
                    f"migrated={migrated_cols}, model={model_cols}"
                )
    finally:
        engine.dispose()


def test_alembic_downgrade_base_drops_domain_tables():
    """alembic downgrade base drops all domain tables, keeps alembic_version."""
    cfg = _alembic_config()
    command.downgrade(cfg, "base")

    from sqlalchemy import create_engine
    engine = create_engine(PG_URL.replace("+asyncpg", ""), future=True)
    try:
        tables = _table_names(engine)
        domain_tables = {
            "users",
            "licenses",
            "machine_activations",
            "subscriptions",
            "webhook_events",
            "audit_log",
        }
        remaining = domain_tables.intersection(set(tables))
        assert not remaining, f"Domain tables not dropped: {remaining}"
        assert "alembic_version" in tables
    finally:
        engine.dispose()


def test_alembic_upgrade_idempotent_rerun():
    """Re-running upgrade after downgrade succeeds (idempotent cycle)."""
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    from sqlalchemy import create_engine
    engine = create_engine(PG_URL.replace("+asyncpg", ""), future=True)
    try:
        tables = _table_names(engine)
        expected = {
            "users",
            "licenses",
            "machine_activations",
            "subscriptions",
            "webhook_events",
            "audit_log",
            "alembic_version",
        }
        assert expected.issubset(set(tables)), f"Missing tables after re-upgrade: {expected - set(tables)}"
    finally:
        engine.dispose()


def test_current_revision_is_head():
    """alembic current reports 0001_initial (head)."""
    cfg = _alembic_config()
    # Ensure at head
    command.upgrade(cfg, "head")
    # Re-run to get current
    from sqlalchemy import create_engine
    engine = create_engine(PG_URL.replace("+asyncpg", ""), future=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            assert row is not None, "alembic_version row missing"
            assert row[0] == "0001_initial", f"Current revision not head: {row[0]}"
    finally:
        engine.dispose()
