"""
DJ AI OS — Audit Service

Writes immutable audit trail entries to DB.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.server.db.models import AuditLog


async def log_audit(
    session: AsyncSession,
    action: str,
    actor: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict | str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Insert an audit log entry.

    Args:
        session: AsyncSession
        action: short action string (e.g., "license.activated")
        actor: user_id, "system", "stripe_webhook", or None
        target_type: "license", "user", "subscription", etc.
        target_id: target entity ID
        details: dict or JSON string
        ip_address: client IP (IPv4/IPv6)
    """
    if isinstance(details, dict):
        details_json = json.dumps(details, default=str)
    else:
        details_json = details

    entry = AuditLog(
        action=action,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        details=details_json,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_audit_logs(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    target_type: Optional[str] = None,
) -> list[AuditLog]:
    """Fetch audit logs with optional filters."""
    from sqlalchemy import select

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
