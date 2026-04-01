"""add conversation chat_mode

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-27

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "chat_mode",
            sa.String(length=16),
            nullable=False,
            server_default="playground",
        ),
    )
    op.execute("UPDATE conversations SET chat_mode = 'ai_twin' WHERE link_token IS NOT NULL")
    op.alter_column("conversations", "chat_mode", server_default=None)


def downgrade() -> None:
    op.drop_column("conversations", "chat_mode")
