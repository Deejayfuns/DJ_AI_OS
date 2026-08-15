"""
DJ AI OS — Dev Database Seeding

Run: python -m app.server.db.seed
"""

import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from app.server.db.connection import init_db, get_db_session
from app.server.db.models import User, License, MachineActivation, Subscription, AuditLog
from app.license.entitlements import EntitlementManager


async def seed() -> None:
    """Insert demo data for local development."""
    await init_db()

    async with get_db_session() as session:
        # Idempotency check
        from sqlalchemy import select, func

        existing = await session.scalar(
            select(func.count(User.id)).where(User.email == "demo@dj-ai-os.local")
        )
        if existing:
            print("[SKIP] Dev database already seeded (demo@dj-ai-os.local exists).")
            return

        # ─── Demo User ───
        demo_user = User(
            id=secrets.token_hex(16),
            email="demo@dj-ai-os.local",
            name="Demo DJ",
            is_admin=False,
            is_active=True,
        )
        session.add(demo_user)

        # ─── Admin User ───
        admin_user = User(
            id=secrets.token_hex(16),
            email="admin@dj-ai-os.local",
            name="Admin",
            is_admin=True,
            is_active=True,
        )
        session.add(admin_user)

        await session.flush()  # get IDs

        # ─── Demo License (PRO) ───
        demo_license = License(
            id=secrets.token_hex(16),
            user_id=demo_user.id,
            key=f"PRO-{secrets.token_hex(20).upper()}",
            plan="PRO",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            max_tracks=EntitlementManager.PLAN_FEATURES["PRO"]["max_tracks"],
            updates_until=datetime.now(timezone.utc) + timedelta(days=90),
            is_active=True,
            signature_nonce=secrets.token_hex(32),
        )
        session.add(demo_license)

        # ─── Demo Machine Activation ───
        machine_act = MachineActivation(
            id=secrets.token_hex(16),
            license_id=demo_license.id,
            machine_id="demo-machine-" + secrets.token_hex(16),
            is_active=True,
            max_machines=3,
        )
        session.add(machine_act)

        # ─── Demo Subscription ───
        demo_sub = Subscription(
            id=secrets.token_hex(16),
            user_id=demo_user.id,
            stripe_customer_id=f"cus_demo_{secrets.token_hex(12)}",
            stripe_subscription_id=f"sub_demo_{secrets.token_hex(12)}",
            stripe_price_id="price_pro_monthly",
            plan="PRO",
            status="active",
            current_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=15),
            cancel_at=None,
        )
        session.add(demo_sub)

        # ─── Audit Log entries ───
        audit_entries = [
            AuditLog(
                action="user.created",
                actor="system",
                target_type="user",
                target_id=demo_user.id,
                details='{"email": "demo@dj-ai-os.local"}',
            ),
            AuditLog(
                action="license.issued",
                actor="system",
                target_type="license",
                target_id=demo_license.id,
                details='{"plan": "PRO", "key": "' + demo_license.key + '"}',
            ),
            AuditLog(
                action="machine.activated",
                actor="demo@dj-ai-os.local",
                target_type="license",
                target_id=demo_license.id,
                details='{"machine_id": "' + machine_act.machine_id + '"}',
            ),
        ]
        session.add_all(audit_entries)

        await session.commit()

    print("[OK] Dev database seeded:")
    print(f"   Demo user:    {demo_user.email}")
    print(f"   Admin user:   {admin_user.email}")
    print(f"   License key:  {demo_license.key}")
    print(f"   Machine ID:   {machine_act.machine_id}")
    print(f"   Subscription: {demo_sub.stripe_subscription_id}")


if __name__ == "__main__":
    asyncio.run(seed())