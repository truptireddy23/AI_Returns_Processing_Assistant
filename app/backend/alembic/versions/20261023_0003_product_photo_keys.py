"""Point every product at its catalog image (app/frontend/public/products/<SKU>.png).

Data-only: databases seeded before product images existed (e.g. Neon) get their
photo keys filled in; new seeds set them directly.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE products SET photo_key = '/products/' || sku || '.png' WHERE photo_key IS NULL"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE products SET photo_key = NULL WHERE photo_key = '/products/' || sku || '.png'"
    )
