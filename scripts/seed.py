#!/usr/bin/env python3
"""Seed the Fineas database with assets and historical snapshots from CSV files.

Asset naming strategy: "simplified names" from snapshots.csv are canonical.
  - 3 stock ETFs (Vanguard FTSE All-World, iShares MSCI World, iShares MSCI EM)
    are consolidated into a single "Stocks" asset.
  - "isyBank Liquidity" → "Cash"
  - "Fonchim Crescita"  → "Fonchim"
  - P2P Lending assets (Esketit, Estateguru, Robocash) → AssetType.OTHER
  - "House" is seeded as an asset even though it has no snapshot history yet.

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

# ---------------------------------------------------------------------------
# Canonical asset definitions
# annualized_return_pct is capped at Numeric(6, 4) — 4 decimal places.
# ---------------------------------------------------------------------------
ASSETS: list[dict] = [
    {
        "name": "Cash",
        "asset_type": AssetType.CASH,
        "annualized_return_pct": Decimal("0.0000"),
    },
    {
        # Consolidates: Vanguard FTSE All-World (0.085), iShares MSCI World (0.086),
        # iShares MSCI EM (0.078). Using Vanguard FTSE All-World as the reference rate.
        "name": "Stocks",
        "asset_type": AssetType.STOCKS,
        "annualized_return_pct": Decimal("0.0850"),
    },
    {
        "name": "Bonds",
        "asset_type": AssetType.BONDS,
        "annualized_return_pct": Decimal("-0.0262"),
    },
    {
        # 0.03985 rounded to 4 decimal places
        "name": "Xtrackers EUR Overnight",
        "asset_type": AssetType.CASH,
        "annualized_return_pct": Decimal("0.0399"),
    },
    {
        "name": "Lyxor SMART",
        "asset_type": AssetType.CASH,
        "annualized_return_pct": Decimal("0.0390"),
    },
    {
        "name": "Esketit",
        "asset_type": AssetType.OTHER,
        "annualized_return_pct": Decimal("0.1280"),
    },
    {
        "name": "Estateguru",
        "asset_type": AssetType.OTHER,
        "annualized_return_pct": Decimal("0.1000"),
    },
    {
        # 0.01027 rounded to 4 decimal places
        "name": "Robocash",
        "asset_type": AssetType.OTHER,
        "annualized_return_pct": Decimal("0.0103"),
    },
    {
        "name": "Fonchim",
        "asset_type": AssetType.PENSION_FUND,
        "annualized_return_pct": Decimal("0.0400"),
    },
    {
        "name": "House",
        "asset_type": AssetType.REAL_ESTATE,
        "annualized_return_pct": Decimal("0.0200"),
    },
]


async def seed_assets(session: AsyncSession) -> dict[str, object]:
    """Insert assets, skip any that already exist. Returns name → UUID map."""
    for asset_def in ASSETS:
        stmt = (
            pg_insert(Asset)
            .values(**asset_def)
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await session.execute(stmt)

    await session.commit()

    result = await session.execute(select(Asset.id, Asset.name))
    asset_ids = {name: uid for uid, name in result.all()}
    print(f"  Assets in DB: {len(asset_ids)}")
    return asset_ids


async def seed_snapshots(session: AsyncSession, asset_ids: dict[str, object]) -> None:
    """Insert snapshots from snapshots.csv, skipping duplicates."""
    csv_path = DATA_DIR / "snapshots.csv"
    inserted = skipped_dup = skipped_unknown = 0

    with open(csv_path, newline="") as f:
        # skipinitialspace strips leading whitespace after commas in header + values
        reader = csv.DictReader(f, skipinitialspace=True)
        rows = list(reader)

    for row in rows:
        asset_name = row["asset_name"].strip()
        if asset_name not in asset_ids:
            skipped_unknown += 1
            print(f"  WARNING: No asset named '{asset_name}' — row skipped")
            continue

        # snapshots.csv date format: DD/MM/YYYY
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

    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=== Seeding assets ===")
        asset_ids = await seed_assets(session)

        print("\n=== Seeding snapshots ===")
        await seed_snapshots(session, asset_ids)

    await engine.dispose()
    print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(main())
