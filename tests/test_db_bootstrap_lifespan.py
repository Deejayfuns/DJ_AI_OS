"""
Regression test — P0-1 production DB root cause.

Production DB-backed routes (POST /api/activate with a valid-format key,
POST /api/checkout) returned 500 because the schema was never created: the
intended ``init_db()`` bootstrap was dead code in ``run.py`` (never wired into
app startup), and Alembic had not been applied to the production DB. Non-DB
routes worked, which is why the outage looked like "just the DB layer".

This test proves the app's FastAPI lifespan now bootstraps the schema on a
fresh (empty) database, so those DB-backed routes return clean application
responses instead of a missing-table 500.
"""

import asyncio
import os

from fastapi.testclient import TestClient

from app.server.api import create_app
from app.server.db.connection import close_db, reset_db


def test_lifespan_bootstraps_schema_so_db_routes_work(tmp_path, monkeypatch):
    """A fresh empty DB gets its schema created by the startup lifespan."""
    # Point at a brand-new, empty SQLite file (no tables, like a fresh prod DB).
    db_file = tmp_path / "bootstrap_test.db"
    monkeypatch.setenv("DJ_AI_OS_DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    # Clear any cached engine so the new URL is picked up at startup.
    asyncio.run(reset_db())

    app = create_app()
    try:
        with TestClient(app) as client:
            # DB-backed route on an empty DB: must be a clean application
            # response (license simply not present), NOT a 500 from a missing
            # "licenses" table.
            r = client.post(
                "/api/activate",
                json={
                    "email": "t@t.com",
                    "license_key": "PRO-1234567890ABCDEF",
                    "machine_id": "m1",
                },
            )
            assert r.status_code == 400
            assert r.json()["detail"] == "LICENSE_NOT_FOUND"

            # Checkout: the DB find/create-user path works (not a DB 500).
            # Stripe is intentionally disabled in this environment, so the
            # only possible non-500 outcome is a Stripe/plan error — never a
            # missing-table 500.
            r2 = client.post("/api/checkout", json={"plan": "PRO", "email": "t@t.com"})
            assert r2.status_code != 500
    finally:
        asyncio.run(close_db())
