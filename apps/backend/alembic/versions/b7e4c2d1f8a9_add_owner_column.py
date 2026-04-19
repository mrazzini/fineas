"""add owner discriminator to assets and asset_snapshots

Revision ID: b7e4c2d1f8a9
Revises: a3f9c1e2b4d5
Create Date: 2026-04-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e4c2d1f8a9"
down_revision: Union[str, None] = "a3f9c1e2b4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Assets: add owner column, backfill existing rows to 'demo', swap
    # UNIQUE(name) for UNIQUE(owner, name) so demo+real can share names.
    op.add_column(
        "assets",
        sa.Column("owner", sa.String(10), nullable=False, server_default="demo"),
    )
    op.create_index("ix_assets_owner", "assets", ["owner"])

    # The original UNIQUE on assets.name was declared inline, so Postgres
    # named the constraint assets_name_key by default.
    op.drop_constraint("assets_name_key", "assets", type_="unique")
    op.create_unique_constraint("uq_asset_owner_name", "assets", ["owner", "name"])

    # Snapshots: mirror the owner for cheap filtering.
    op.add_column(
        "asset_snapshots",
        sa.Column("owner", sa.String(10), nullable=False, server_default="demo"),
    )
    op.create_index("ix_asset_snapshots_owner", "asset_snapshots", ["owner"])


def downgrade() -> None:
    op.drop_index("ix_asset_snapshots_owner", table_name="asset_snapshots")
    op.drop_column("asset_snapshots", "owner")

    op.drop_constraint("uq_asset_owner_name", "assets", type_="unique")
    op.create_unique_constraint("assets_name_key", "assets", ["name"])

    op.drop_index("ix_assets_owner", table_name="assets")
    op.drop_column("assets", "owner")
