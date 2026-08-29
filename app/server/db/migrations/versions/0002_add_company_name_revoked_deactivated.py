"""add company_name, revoked_at, deactivated_at

Revision ID: 0002_company_revoked_deactivated
Revises: 0001_initial
Create Date: 2026-08-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_company_revoked_deactivated"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add company_name to users
    op.add_column(
        "users",
        sa.Column("company_name", sa.String(length=120), nullable=True),
    )

    # Add revoked_at to licenses
    op.add_column(
        "licenses",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add deactivated_at to machine_activations
    op.add_column(
        "machine_activations",
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("machine_activations", "deactivated_at")
    op.drop_column("licenses", "revoked_at")
    op.drop_column("users", "company_name")