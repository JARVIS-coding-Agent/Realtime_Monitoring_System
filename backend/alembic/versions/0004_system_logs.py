"""create system_logs table

Revision ID: 0004_system_logs
Revises: 0003_realtime_data
Create Date: 2026-10-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_system_logs"
down_revision: Union[str, None] = "0003_realtime_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_system_logs_level", "system_logs", ["level"])
    op.create_index("ix_system_logs_user_id", "system_logs", ["user_id"])
    op.create_index("ix_system_logs_created_at", "system_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_system_logs_created_at", table_name="system_logs")
    op.drop_index("ix_system_logs_user_id", table_name="system_logs")
    op.drop_index("ix_system_logs_level", table_name="system_logs")
    op.drop_table("system_logs")
