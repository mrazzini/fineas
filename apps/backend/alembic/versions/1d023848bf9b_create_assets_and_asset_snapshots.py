"""create assets and asset_snapshots

Revision ID: 1d023848bf9b
Revises:
Create Date: 2026-03-18 21:57:24.665188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '1d023848bf9b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- assets table --
    # The Enum column auto-creates the asset_type_enum type in PostgreSQL.
    op.create_table(
        'assets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column(
            'asset_type',
            sa.Enum(
                'CASH', 'STOCKS', 'BONDS', 'REAL_ESTATE',
                'CRYPTO', 'PENSION_FUND', 'OTHER',
                name='asset_type_enum',
            ),
            nullable=False,
        ),
        sa.Column('annualized_return_pct', sa.Numeric(6, 4), nullable=True),
        sa.Column('ticker', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # -- asset_snapshots table --
    op.create_table(
        'asset_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'asset_id', UUID(as_uuid=True),
            sa.ForeignKey('assets.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('snapshot_date', sa.Date, nullable=False),
        sa.Column('balance', sa.Numeric(15, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('asset_id', 'snapshot_date', name='uq_snapshot_asset_date'),
    )


def downgrade() -> None:
    op.drop_table('asset_snapshots')
    op.drop_table('assets')
    sa.Enum(name='asset_type_enum').drop(op.get_bind(), checkfirst=True)
