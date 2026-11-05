"""Return messages: the chat thread between a customer and a return's reviewer,
auto-answered by the AI assistant until a reviewer takes it over.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05 20:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "return_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("return_id", sa.UUID(), nullable=False),
        sa.Column(
            "sender",
            sa.Enum(
                "customer",
                "reviewer",
                "bot",
                name="message_sender",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("sender_user_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["return_id"],
            ["returns.id"],
            name=op.f("fk_return_messages_return_id_returns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            name=op.f("fk_return_messages_sender_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_return_messages")),
    )
    op.create_index(
        "ix_return_messages_return_created", "return_messages", ["return_id", "created_at"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_return_messages_return_created", table_name="return_messages")
    op.drop_table("return_messages")
