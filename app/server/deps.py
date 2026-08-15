"""
DJ AI OS — FastAPI Dependencies

Provides DB session injection and admin auth verification.
"""

import os
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.server.db.connection import get_db_session


# ─── DB Session Dependency ───

async def get_session() -> AsyncSession:
    """Inject AsyncSession into FastAPI routes."""
    async with get_db_session() as session:
        yield session


# ─── Admin Auth ───

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()


security = HTTPBearer(auto_error=False)


def get_admin_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    Verify admin token from Authorization header.

    Returns the token if valid, raises HTTP 401 if not.
    """
    if not ADMIN_TOKEN:
        # Admin token not set — reject all admin access
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ADMIN_AUTH_NOT_CONFIGURED",
        )

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MISSING_BEARER_TOKEN",
        )

    if not secrets.compare_digest(credentials.credentials, ADMIN_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_ADMIN_TOKEN",
        )

    return credentials.credentials


def is_admin_configured() -> bool:
    """Whether admin auth is enabled."""
    return bool(ADMIN_TOKEN)
