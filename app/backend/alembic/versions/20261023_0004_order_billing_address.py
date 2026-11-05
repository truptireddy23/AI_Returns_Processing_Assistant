"""Add the billing address to orders.

Nullable: orders placed before billing was collected were billed to the
shipping address, and the API shows them that way.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("billing_name", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("billing_line1", sa.String(length=200), nullable=True))
    op.add_column("orders", sa.Column("billing_city", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("billing_postal_code", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "billing_postal_code")
    op.drop_column("orders", "billing_city")
    op.drop_column("orders", "billing_line1")
    op.drop_column("orders", "billing_name")
