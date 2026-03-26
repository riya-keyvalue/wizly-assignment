"""add_shareable_links

Revision ID: 0003
Revises: 86c12eb82197
Create Date: 2026-03-26 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "86c12eb82197"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create shareable_links table
    op.create_table(
        "shareable_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_shareable_links_owner_id", "shareable_links", ["owner_id"])
    op.create_index("ix_shareable_links_token", "shareable_links", ["token"])

    # Make conversations.user_id nullable to support anonymous shared conversations
    op.alter_column("conversations", "user_id", existing_type=sa.Uuid(), nullable=True)

    # Add link_token FK and owner_id to conversations
    op.add_column("conversations", sa.Column("link_token", sa.String(64), nullable=True))
    op.add_column("conversations", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_link_token",
        "conversations",
        "shareable_links",
        ["link_token"],
        ["token"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_conversations_owner_id",
        "conversations",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_link_token", "conversations", ["link_token"])


def downgrade() -> None:
    op.drop_index("ix_conversations_link_token", table_name="conversations")
    op.drop_constraint("fk_conversations_owner_id", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_link_token", "conversations", type_="foreignkey")
    op.drop_column("conversations", "owner_id")
    op.drop_column("conversations", "link_token")
    op.alter_column("conversations", "user_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_index("ix_shareable_links_token", table_name="shareable_links")
    op.drop_index("ix_shareable_links_owner_id", table_name="shareable_links")
    op.drop_table("shareable_links")
