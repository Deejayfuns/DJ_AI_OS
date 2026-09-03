"""
DJ AI OS — Server Entrypoint

Run: uvicorn app.server.run:app --reload --port 8000
Or: python -m app.server.run
"""

import os
import sys

# Production startup validation (runs before app creation)
from app.server.startup_validation import run_startup_validation

from app.server.api import create_app


# Run production validation FIRST - fail fast if critical config missing
run_startup_validation()


# Schema bootstrap (idempotent create_all) is wired into the FastAPI lifespan
# inside create_app() — see _bootstrap_lifespan in app/server/api.py.
app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DJ_AI_OS_API_PORT", "8000"))
    uvicorn.run(
        "app.server.run:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("DJ_AI_OS_API_RELOAD", "false").lower() == "true",
    )
