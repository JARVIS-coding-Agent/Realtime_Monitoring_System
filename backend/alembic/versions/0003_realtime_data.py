"""create realtime_data table

Revision ID: 0003_realtime_data
Revises: 0002_data_records
Create Date: 2026-10-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_realtime_data"
down_revision: Union[str, None] = "0002_data_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "realtime_data",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_realtime_data_generated_at", "realtime_data", ["generated_at"])


def downgrade() -> None:
    op.drop_index("ix_realtime_data_generated_at", table_name="realtime_data")
    op.drop_table("realtime_data")
