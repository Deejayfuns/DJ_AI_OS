"""
DJ AI OS — SQLAlchemy 2.0 Async ORM Models

PostgreSQL (prod) / SQLite (dev) schema for commercial license server.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class with common configuration."""
    pass


class User(Base):
    """Platform users (customers + admins)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    licenses: Mapped[list["License"]] = relationship(back_populates="user", lazy="selectin")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} admin={self.is_admin}>"


class License(Base):
    """Issued license records (one per user per plan)."""

    __tablename__ = "licenses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # PRO-XXXXX
    plan: Mapped[str] = mapped_column(String(32), nullable=False)  # PRO | DJ_ARCHIVE | STUDIO | ENTERPRISE
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_tracks: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    updates_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Ed25519 signature metadata
    signature_nonce: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="licenses", lazy="selectin")
    machine_activations: Mapped[list["MachineActivation"]] = relationship(
        back_populates="license", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_licenses_user_plan", "user_id", "plan"),
    )

    def __repr__(self) -> str:
        return f"<License id={self.id} key={self.key} plan={self.plan} active={self.is_active}>"


class MachineActivation(Base):
    """Machine activations per license (enforces max_machines per plan)."""

    __tablename__ = "machine_activations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    license_id: Mapped[str] = mapped_column(String(32), ForeignKey("licenses.id"), index=True, nullable=False)
    machine_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_machines: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # plan limit at activation time

    # Relationships
    license: Mapped["License"] = relationship(back_populates="machine_activations", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("license_id", "machine_id", name="uq_license_machine"),
        Index("ix_machine_activations_license_active", "license_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<MachineActivation id={self.id} license={self.license_id} machine={self.machine_id[:8]}...>"


class Subscription(Base):
    """Stripe subscription records."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True, nullable=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)  # PRO | DJ_ARCHIVE | STUDIO | ENTERPRISE
    status: Mapped[str] = mapped_column(
        String(32), default="incomplete", nullable=False
    )  # active | past_due | cancelled | trialing | incomplete | incomplete_expired
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions", lazy="selectin")

    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user={self.user_id} plan={self.plan} status={self.status}>"


class WebhookEvent(Base):
    """Stripe webhook events (idempotency key storage)."""

    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Stripe event ID (evt_xxx)
    type: Mapped[str] = mapped_column(String(128), nullable=False)  # checkout.session.completed, etc.
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 of raw body

    __table_args__ = (
        Index("ix_webhook_events_type_processed", "type", "processed"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent id={self.id} type={self.type} processed={self.processed}>"


class AuditLog(Base):
    """Immutable audit trail for all sensitive operations."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # license.activated, webhook.received, etc.
    actor: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # user_id, "system", "stripe_webhook"
    target_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # "license", "user", "subscription"
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4/IPv6
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_log_actor_created", "actor", "created_at"),
        Index("ix_audit_log_target", "target_type", "target_id"),
        Index("ix_audit_log_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} actor={self.actor}>"