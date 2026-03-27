#!/usr/bin/env python3
"""Seed the Fineas database with assets and historical snapshots from CSV files.

By default, reads from data/example_assets.csv and data/example_snapshots.csv
(fictional demo data tracked in git). To use real personal data instead, set:

    SEED_ASSETS_CSV=data/assets.csv  SEED_SNAPSHOTS_CSV=data/snapshots.csv

Usage (from repo root):
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost/fineas python scripts/seed.py
"""

import asyncio
import csv
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add the backend package to sys.path so we can reuse models.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import Asset, AssetSnapshot, AssetType

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Asset type mapping from CSV values to enum
ASSET_TYPE_MAP = {
    "CASH": AssetType.CASH,
    "STOCKS": AssetType.STOCKS,
    "BONDS": AssetType.BONDS,
    "REAL_ESTATE": AssetType.REAL_ESTATE,
    "CRYPTO": AssetType.CRYPTO,
    "PENSION_FUND": AssetType.PENSION_FUND,
    "OTHER": AssetType.OTHER,
}


async def seed_assets(session: AsyncSession, csv_path: Path) -> dict[str, object]:
    """Insert assets from CSV, skip any that already exist. Returns name -> UUID map."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        rows = list(reader)

    for row in rows:
        name = row["name"].strip()
        asset_type = ASSET_TYPE_MAP[row["asset_type"].strip()]
        annualized_return_pct = Decimal(row["annualized_return_pct"].strip())

        stmt = (
            pg_insert(Asset)
            .values(
                name=name,
                asset_type=asset_type,
                annualized_return_pct=annualized_return_pct,
            )
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await session.execute(stmt)

    await session.commit()

    result = await session.execute(select(Asset.id, Asset.name))
    asset_ids = {name: uid for uid, name in result.all()}
    print(f"  Assets in DB: {len(asset_ids)}")
    return asset_ids


async def seed_snapshots(
    session: AsyncSession, asset_ids: dict[str, object], csv_path: Path
) -> None:
    """Insert snapshots from CSV, skipping duplicates."""
    inserted = skipped_dup = skipped_unknown = 0

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        rows = list(reader)

    for row in rows:
        asset_name = row["asset_name"].strip()
        if asset_name not in asset_ids:
            skipped_unknown += 1
            print(f"  WARNING: No asset named '{asset_name}' — row skipped")
            continue

        # snapshots CSV date format: DD/MM/YYYY
        day, month, year = row["snapshot_date"].strip().split("/")
        snap_date = date(int(year), int(month), int(day))
        balance = Decimal(row["balance"].strip())

        stmt = (
            pg_insert(AssetSnapshot)
            .values(
                asset_id=asset_ids[asset_name],
                snapshot_date=snap_date,
                balance=balance,
            )
            .on_conflict_do_nothing(constraint="uq_snapshot_asset_date")
        )
        result = await session.execute(stmt)
        if result.rowcount:
            inserted += 1
        else:
            skipped_dup += 1

    await session.commit()
    print(
        f"  Snapshots: {inserted} inserted, "
        f"{skipped_dup} skipped (duplicate), "
        f"{skipped_unknown} skipped (unknown asset)"
    )


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("ERROR: DATABASE_URL environment variable is not set.")

    assets_csv = Path(os.environ.get("SEED_ASSETS_CSV", DATA_DIR / "example_assets.csv"))
    snapshots_csv = Path(os.environ.get("SEED_SNAPSHOTS_CSV", DATA_DIR / "example_snapshots.csv"))

    print(f"  Assets CSV:    {assets_csv}")
    print(f"  Snapshots CSV: {snapshots_csv}")

    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n=== Seeding assets ===")
        asset_ids = await seed_assets(session, assets_csv)

        print("\n=== Seeding snapshots ===")
        await seed_snapshots(session, asset_ids, snapshots_csv)

    await engine.dispose()
    print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(main())
