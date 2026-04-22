"""wipe asset + snapshot data for a clean relaunch

One-shot cleanup requested by the owner. After collapsing the demo/real
split the real-owner rows that had been uploaded are no longer needed;
the site is being relaunched with an empty owner portfolio. The schema
is unchanged — this migration only empties the two data tables.

Revision ID: d9a2f7e3b1c4
Revises: c8f5a3b9e2d1
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "d9a2f7e3b1c4"
down_revision: Union[str, None] = "c8f5a3b9e2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CASCADE covers the FK from asset_snapshots to assets, and RESTART
    # IDENTITY resets any sequences (there are none on UUID PKs, but it's
    # harmless and keeps the statement honest about its intent).
    op.execute(
        "TRUNCATE TABLE asset_snapshots, assets RESTART IDENTITY CASCADE"
    )


def downgrade() -> None:
    # Data deletion is not reversible — downgrade is a no-op so Alembic's
    # chain stays consistent if someone rolls back through this revision.
    pass
