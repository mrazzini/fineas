#!/usr/bin/env python3
"""Seed the Fineas database with demo assets and snapshots from CSV files.

Loads into the `demo` owner scope so the data is visible to unauthenticated
visitors on the public dashboard.  Real personal data is loaded via the
authenticated `POST /data/load` endpoint instead.

Usage (from repo root):
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost/fineas python scripts/seed.py
"""
import asyncio
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.loader import load_portfolio

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f, skipinitialspace=True))


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("ERROR: DATABASE_URL environment variable is not set.")

    assets_csv = Path(os.environ.get("SEED_ASSETS_CSV", DATA_DIR / "example_assets.csv"))
    snapshots_csv = Path(
        os.environ.get("SEED_SNAPSHOTS_CSV", DATA_DIR / "example_snapshots.csv")
    )

    print(f"  Assets CSV:    {assets_csv}")
    print(f"  Snapshots CSV: {snapshots_csv}")

    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await load_portfolio(
            session,
            assets_rows=_read_csv(assets_csv),
            snapshots_rows=_read_csv(snapshots_csv),
            owner="demo",
        )

    await engine.dispose()
    print(
        f"\nSeed complete: {result.assets_inserted} assets, "
        f"{result.snapshots_inserted} snapshots, {len(result.skipped)} skipped."
    )
    for note in result.skipped:
        print(f"  WARNING: {note}")


if __name__ == "__main__":
    asyncio.run(main())
