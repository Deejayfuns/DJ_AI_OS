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
    machine_id: Optional[str] = None
    expiry: Optional[str] = None
    updates_until: Optional[str] = None
    max_tracks: Optional[int] = None


class CreateCustomerRequest(BaseModel):
    email: str
    name: str
    company_name: Optional[str] = None


class UserActiveRequest(BaseModel):
    is_active: bool


class RevokeLicenseRequest(BaseModel):
    license_id: str


class CancelSubscriptionRequest(BaseModel):
    subscription_id: str


class DeactivateMachineRequest(BaseModel):
    license_id: str
    machine_id: str


class RenewLicenseRequest(BaseModel):
    months: int = 12


class ChangePlanRequest(BaseModel):
    plan: str


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
    result = await service.issue_license(
        req.user_id,
        req.plan,
        req.months,
        machine_id=req.machine_id,
        expiry=req.expiry,
        updates_until=req.updates_until,
        max_tracks=req.max_tracks,
    )
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


@auth_router.post("/licenses/{license_id}/machines/{machine_id}/deactivate")
async def deactivate_machine(
    license_id: str,
    machine_id: str,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    ok = await service.deactivate_machine(license_id, machine_id, actor="admin")
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_OR_MACHINE_NOT_FOUND")
    return {"ok": True, "license_id": license_id, "machine_id": machine_id}


@auth_router.post("/licenses/{license_id}/renew")
async def renew_license(
    license_id: str,
    req: RenewLicenseRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    result = await service.renew_license(license_id, req.months, actor="admin")
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_NOT_FOUND")
    return {"ok": True, "license": result}


@auth_router.post("/licenses/{license_id}/change-plan")
async def change_license_plan(
    license_id: str,
    req: ChangePlanRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AdminService(session)
    result = await service.change_license_plan(license_id, req.plan, actor="admin")
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_NOT_FOUND")
    return {"ok": True, "license": result}


@auth_router.get("/licenses/{license_id}/download")
async def download_license(
    license_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Download signed license file for customer offline activation."""
    service = AdminService(session)
    license_data = await service.get_license_detail(license_id)
    if not license_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_NOT_FOUND")

    # Generate canonical license payload matching LicenseSchema.validate_structure()
    # Required fields: machine_id, plan, expiry, max_tracks, updates_until, issued_at, nonce, signature
    from datetime import datetime, timezone
    from app.license import signature as sig
    from app.license.entitlements import EntitlementManager
    import secrets

    # Get the full license record with user info
    from app.server.db.models import License
    result = await session.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LICENSE_NOT_FOUND")

    # Get machine_id from active machine activation (or use provided one)
    machine_id = None
    for m in lic.machine_activations:
        if m.is_active:
            machine_id = m.machine_id
            break

    if not machine_id:
        # No active machine - use a placeholder (will fail machine check on client)
        machine_id = "0" * 64

    # Build license payload for signing
    payload = {
        "email": lic.user.email if lic.user else "",
        "machine_id": machine_id,
        "plan": lic.plan,
        "expiry": lic.expires_at.strftime("%Y-%m-%d") if lic.expires_at else "2099-12-31",
        "max_tracks": lic.max_tracks,
        "updates_until": lic.updates_until.strftime("%Y-%m-%d") if lic.updates_until else "2099-12-31",
        "issued_at": lic.issued_at.isoformat().replace("+00:00", "Z") if lic.issued_at else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "nonce": lic.signature_nonce,
    }

    # Sign with vendor private key
    signature_hex = sig.sign(payload)
    payload["signature"] = signature_hex

    # Audit log
    from app.server.services.audit_service import log_audit
    await log_audit(
        session,
        action="license.downloaded",
        actor="admin",
        target_type="license",
        target_id=license_id,
        details={"key": lic.key, "plan": lic.plan},
    )

    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f"attachment; filename=customer_{license_id}.key"},
        media_type="application/json",
    )


# ─── Customers ───

@auth_router.post("/customers")
async def create_customer(
    req: CreateCustomerRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new customer (User)."""
    from app.server.db.models import User
    from secrets import token_hex

    # Check email uniqueness
    existing = await session.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EMAIL_ALREADY_EXISTS")

    user = User(
        id=token_hex(16),
        email=req.email,
        name=req.name,
        company_name=req.company_name,
        is_admin=False,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    # Audit
    from app.server.services.audit_service import log_audit
    await log_audit(
        session,
        action="customer.created",
        actor="admin",
        target_type="user",
        target_id=user.id,
        details={"email": req.email, "name": req.name, "company_name": req.company_name},
    )

    return {
        "ok": True,
        "customer": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company_name": user.company_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
    }


@auth_router.get("/customers")
async def list_customers(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """List customers (Users)."""
    from app.server.db.models import User

    stmt = select(User).order_by(User.created_at.desc())
    if search:
        stmt = stmt.where(User.email.ilike(f"%{search}%"))
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "company_name": u.company_name,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@auth_router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get customer detail with licenses."""
    from app.server.db.models import User

    result = await session.execute(select(User).where(User.id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CUSTOMER_NOT_FOUND")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "company_name": user.company_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


@auth_router.get("/customers/{customer_id}/licenses")
async def get_customer_licenses(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get licenses for a customer."""
    from app.server.db.models import User, License

    result = await session.execute(select(User).where(User.id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CUSTOMER_NOT_FOUND")

    result = await session.execute(
        select(License).where(License.user_id == customer_id).order_by(License.issued_at.desc())
    )
    licenses = result.scalars().all()

    return [
        {
            "id": l.id,
            "key": l.key,
            "plan": l.plan,
            "issued_at": l.issued_at.isoformat(),
            "expires_at": l.expires_at.isoformat(),
            "max_tracks": l.max_tracks,
            "is_active": l.is_active,
        }
        for l in licenses
    ]


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