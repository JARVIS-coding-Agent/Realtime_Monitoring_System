"""create data_records table

Revision ID: 0002_data_records
Revises: 0001_users
Create Date: 2026-10-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_data_records"
down_revision: Union[str, None] = "0001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_data_records_category", "data_records", ["category"])
    op.create_index("ix_data_records_timestamp", "data_records", ["timestamp"])
    op.create_index("ix_data_records_owner_id", "data_records", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_data_records_owner_id", table_name="data_records")
    op.drop_index("ix_data_records_timestamp", table_name="data_records")
    op.drop_index("ix_data_records_category", table_name="data_records")
    op.drop_table("data_records")
