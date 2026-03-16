"""create assets and asset_snapshots

Revision ID: 83e6f24d9eb5
Revises:
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "83e6f24d9eb5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "CASH",
                "STOCKS",
                "BONDS",
                "REAL_ESTATE",
                "CRYPTO",
                "PENSION_FUND",
                "OTHER",
                name="asset_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("annualized_return_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "asset_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("balance", sa.Numeric(15, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "snapshot_date", name="uq_snapshot_asset_date"),
    )


def downgrade() -> None:
    op.drop_table("asset_snapshots")
    op.execute("DROP TYPE IF EXISTS asset_type_enum")
    op.drop_table("assets")
