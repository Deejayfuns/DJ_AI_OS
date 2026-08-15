"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # licenses
    op.create_table(
        "licenses",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_tracks", sa.Integer(), nullable=False, server_default=sa.text("1000")),
        sa.Column("updates_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("signature_nonce", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
    )
    op.create_index("ix_licenses_key", "licenses", ["key"], unique=True)
    op.create_index("ix_licenses_user_id", "licenses", ["user_id"])
    op.create_index("ix_licenses_signature_nonce", "licenses", ["signature_nonce"], unique=True)
    op.create_index("ix_licenses_user_plan", "licenses", ["user_id", "plan"])

    # machine_activations
    op.create_table(
        "machine_activations",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("license_id", sa.String(length=32), nullable=False),
        sa.Column("machine_id", sa.String(length=64), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_machines", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.ForeignKeyConstraint(["license_id"], ["licenses.id"], ),
    )
    op.create_index("ix_machine_activations_license_id", "machine_activations", ["license_id"])
    op.create_index("ix_machine_activations_machine_id", "machine_activations", ["machine_id"])
    op.create_index(
        "ix_machine_activations_license_active",
        "machine_activations",
        ["license_id", "is_active"],
    )
    op.create_unique_constraint("uq_license_machine", "machine_activations", ["license_id", "machine_id"])

    # subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=64), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=64), nullable=True),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'incomplete'")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"])
    op.create_index("ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"])
    op.create_index(
        "ix_subscriptions_user_status",
        "subscriptions",
        ["user_id", "status"],
    )

    # webhook_events
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_webhook_events_type_processed", "webhook_events", ["type", "processed"])

    # audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=True),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_actor_created", "audit_log", ["actor", "created_at"])
    op.create_index("ix_audit_log_target", "audit_log", ["target_type", "target_id"])
    op.create_index("ix_audit_log_action_created", "audit_log", ["action", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("webhook_events")
    op.drop_table("subscriptions")
    op.drop_table("machine_activations")
    op.drop_table("licenses")
    op.drop_table("users")
