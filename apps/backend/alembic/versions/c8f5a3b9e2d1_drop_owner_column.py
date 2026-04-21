"""drop owner column — demo now lives in frontend fixtures

Revision ID: c8f5a3b9e2d1
Revises: b7e4c2d1f8a9
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8f5a3b9e2d1"
down_revision: Union[str, None] = "b7e4c2d1f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Demo rows are no longer served from the DB — they live as a static
    # fixture in the frontend. Purge them before collapsing the schema.
    op.execute("DELETE FROM assets WHERE owner = 'demo'")

    # Snapshots: drop index + owner column (rows were cascade-deleted above
    # when their parent asset was removed, so no manual cleanup needed here).
    op.drop_index("ix_asset_snapshots_owner", table_name="asset_snapshots")
    op.drop_column("asset_snapshots", "owner")

    # Assets: swap the composite UNIQUE back to a plain UNIQUE(name).
    op.drop_constraint("uq_asset_owner_name", "assets", type_="unique")
    op.create_unique_constraint("assets_name_key", "assets", ["name"])
    op.drop_index("ix_assets_owner", table_name="assets")
    op.drop_column("assets", "owner")


def downgrade() -> None:
    op.add_column(
        "assets",
        sa.Column("owner", sa.String(10), nullable=False, server_default="real"),
    )
    op.create_index("ix_assets_owner", "assets", ["owner"])
    op.drop_constraint("assets_name_key", "assets", type_="unique")
    op.create_unique_constraint("uq_asset_owner_name", "assets", ["owner", "name"])

    op.add_column(
        "asset_snapshots",
        sa.Column("owner", sa.String(10), nullable=False, server_default="real"),
    )
    op.create_index("ix_asset_snapshots_owner", "asset_snapshots", ["owner"])
