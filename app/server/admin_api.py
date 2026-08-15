"""
DJ AI OS — Admin API Router

Endpoints for admin dashboard (users, licenses, subscriptions, audit).
Auth: Bearer token (ADMIN_TOKEN env).
"""

from typing import Optional

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from app.server.deps import get_admin_token, get_session
from app.server.services.admin_service import AdminService
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/admin/api", tags=["admin"])

# Router for endpoints that require admin auth (data + mutations)
auth_router = APIRouter(prefix="/admin/api", tags=["admin"], dependencies=[Depends(get_admin_token)])


# ─── Request Models ───

class IssueLicenseRequest(BaseModel):
    user_id: str
    plan: str
    months: int = 12


class UserActiveRequest(BaseModel):
    is_active: bool


class RevokeLicenseRequest(BaseModel):
    license_id: str


class CancelSubscriptionRequest(BaseModel):
    subscription_id: str


# ─── Dashboard Stats ───

@auth_router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    return await service.get_stats()


# ─── Users ───

@auth_router.get("/users")
async def list_users(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    return await service.list_users(limit, offset, search)


@auth_router.get("/users/{user_id}")
async def get_user(user_id: str, session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    user = await service.get_user_detail(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    return user


@auth_router.post("/users/{user_id}/active")
async def set_user_active(
    user_id: str,
    req: UserActiveRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    ok = await service.set_user_active(user_id, req.is_active)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    return {"ok": True, "user_id": user_id, "is_active": req.is_active}


@auth_router.get("/users/{user_id}/licenses")
async def get_user_licenses(user_id: str, session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    return await service.get_user_licenses(user_id)


@auth_router.get("/users/{user_id}/subscription")
async def get_user_subscription(user_id: str, session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    sub = await service.get_user_subscription(user_id)
    if not sub:
        return None
    return sub


@auth_router.get("/users/{user_id}/machines")
async def get_user_machines(user_id: str, session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    return await service.get_user_machines(user_id)


# ─── Licenses ───

@auth_router.get("/licenses")
async def list_licenses(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    plan: Optional[str] = None,
    user_email: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    return await service.list_licenses(limit, offset, plan, user_email)


@auth_router.get("/licenses/{license_id}")
async def get_license(license_id: str, session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    lic = await service.get_license_detail(license_id)
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_NOT_FOUND")
    return lic


@auth_router.post("/licenses/issue")
async def issue_license(
    req: IssueLicenseRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    result = await service.issue_license(req.user_id, req.plan, req.months)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    return {"ok": True, "license": result}


@auth_router.post("/licenses/revoke")
async def revoke_license(
    req: RevokeLicenseRequest,
    token: str = Depends(get_admin_token),
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    ok = await service.revoke_license(req.license_id, actor="admin")
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_NOT_FOUND")
    return {"ok": True, "license_id": req.license_id}


# ─── Subscriptions ───

@auth_router.get("/subscriptions")
async def list_subscriptions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    return await service.list_subscriptions(limit, offset, status_filter)


@auth_router.get("/subscriptions/{sub_id}")
async def get_subscription(sub_id: str, session: AsyncSession = Depends(get_session)):
    service = AdminService(session)
    sub = await service.get_subscription_detail(sub_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SUBSCRIPTION_NOT_FOUND")
    return sub


@auth_router.post("/subscriptions/cancel")
async def cancel_subscription(
    req: CancelSubscriptionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Cancel a Stripe subscription."""
    # Find local subscription
    from app.server.db.models import Subscription

    result = await session.execute(select(Subscription).where(Subscription.id == req.subscription_id))
    local_sub = result.scalar_one_or_none()

    if not local_sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SUBSCRIPTION_NOT_FOUND")

    if not local_sub.stripe_subscription_id:
        # No Stripe subscription — just mark cancelled locally
        local_sub.status = "cancelled"
        local_sub.cancel_at = datetime.now(timezone.utc)
        await session.flush()
        return {"ok": True, "subscription_id": req.subscription_id, "stripe_cancelled": False}

    # Cancel via Stripe
    from app.server.services.stripe_service import stripe_service

    cancel_result = stripe_service.cancel_subscription(local_sub.stripe_subscription_id)
    if not cancel_result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"STRIPE_CANCEL_FAILED: {cancel_result.get('reason')}",
        )

    local_sub.status = "cancelled"
    local_sub.cancel_at = datetime.now(timezone.utc)
    await session.flush()

    # Audit
    from app.server.services.audit_service import log_audit

    await log_audit(
        session,
        action="subscription.cancelled",
        actor="admin",
        target_type="subscription",
        target_id=req.subscription_id,
        details={"stripe_subscription_id": local_sub.stripe_subscription_id},
    )

    return {"ok": True, "subscription_id": req.subscription_id, "stripe_cancelled": True}


# ─── Audit Log ───

@auth_router.get("/audit")
async def list_audit(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    actor: Optional[str] = None,
    target_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    return await service.list_audit_logs(limit, offset, action, actor, target_type)


# ─── Login (token check) ───

@router.post("/login")
async def admin_login(token: str = Depends(get_admin_token)):
    """Verify admin token."""
    return {"ok": True, "authenticated": True}


# ─── Admin Config ───

@router.get("/config")
async def admin_config(token: str = Depends(get_admin_token)):
    """Return whether admin auth is configured."""
    from app.server.deps import is_admin_configured

    return {"admin_auth_enabled": is_admin_configured()}