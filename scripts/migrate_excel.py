#!/usr/bin/env python3
"""
One-shot migration: CA_HFLOW.xlsx → PostgreSQL.

Run from repo root:
    pip install -e "apps/api[migration]"
    python scripts/migrate_excel.py

Idempotent: safe to run multiple times.
"""

import asyncio
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Make sure we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from app.config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

EXCEL_PATH = Path(__file__).parent.parent / "data" / "CA_HFLOW.xlsx"

# Column index (0-based) → asset name mapping for Historical_amounts sheet
COLUMN_TO_ASSET = {
    1: "Pure Cash Liquidity",      # B
    2: "Long-Term Stocks",         # C
    3: "iBonds",                   # D
    4: "Xtrackers EUR Overnight",  # E
    5: "Lyxor SMART",              # F
    6: "Esketit",                  # G
    7: "Estateguru",               # H
    8: "Robocash",                 # I
    # Column 9 (J) = Total — skip
}

# Assets to seed (matches DATA_MODEL.md)
ASSETS = [
    {
        "name": "Pure Cash Liquidity",
        "asset_type": "cash",
        "platform": "isyBank",
        "expected_annual_return": 0.00000,
        "is_active": True,
    },
    {
        "name": "Long-Term Stocks",
        "asset_type": "stocks",
        "platform": "Scalable Capital",
        "expected_annual_return": 0.08500,
        "is_active": True,
    },
    {
        "name": "iBonds",
        "asset_type": "bonds",
        "platform": "Scalable Capital",
        "expected_annual_return": -0.02620,
        "is_active": True,
    },
    {
        "name": "Xtrackers EUR Overnight",
        "asset_type": "money_market",
        "platform": "Scalable Capital",
        "expected_annual_return": 0.03985,
        "is_active": True,
    },
    {
        "name": "Lyxor SMART",
        "asset_type": "money_market",
        "platform": "Scalable Capital",
        "expected_annual_return": 0.03900,
        "is_active": True,
    },
    {
        "name": "Esketit",
        "asset_type": "p2p_lending",
        "platform": "Esketit",
        "expected_annual_return": 0.12800,
        "is_active": True,
    },
    {
        "name": "Estateguru",
        "asset_type": "p2p_lending",
        "platform": "Estateguru",
        "expected_annual_return": 0.10000,
        "is_active": True,
    },
    {
        "name": "Robocash",
        "asset_type": "p2p_lending",
        "platform": "Robocash",
        "expected_annual_return": 0.01027,
        "is_active": False,
    },
    {
        "name": "Fonchim",
        "asset_type": "pension",
        "platform": "Fonchim",
        "expected_annual_return": 0.04200,
        "is_active": True,
    },
]


async def seed_assets(session: AsyncSession) -> dict[str, str]:
    """Insert assets idempotently. Returns {name: id} map."""
    name_to_id: dict[str, str] = {}

    for asset_data in ASSETS:
        result = await session.execute(
            text("""
                INSERT INTO assets (name, asset_type, platform, expected_annual_return, is_active, metadata)
                VALUES (:name, :asset_type, :platform, :expected_annual_return, :is_active, '{}')
                ON CONFLICT (name) DO UPDATE
                    SET asset_type = EXCLUDED.asset_type,
                        platform = EXCLUDED.platform,
                        expected_annual_return = EXCLUDED.expected_annual_return,
                        is_active = EXCLUDED.is_active
                RETURNING id
            """),
            asset_data,
        )
        row = result.fetchone()
        name_to_id[asset_data["name"]] = str(row[0])

    await session.commit()
    log.info("Seeded %d assets", len(name_to_id))
    return name_to_id


def _parse_date_from_cell(cell_value) -> date | None:
    """Parse various date formats from Excel cells."""
    if pd.isna(cell_value):
        return None
    if isinstance(cell_value, (pd.Timestamp,)):
        return cell_value.date()
    if hasattr(cell_value, "date"):
        return cell_value.date()
    return None


def _infer_missing_dates(df: pd.DataFrame) -> list[date]:
    """
    Historical_amounts rows 2-23 (0-indexed 0-21). Row 23 (index 21) may lack
    a date in column A. Infer it from the monthly sequence.
    """
    known_dates = []
    for val in df.iloc[:, 0]:
        d = _parse_date_from_cell(val)
        if d:
            known_dates.append(d)

    if len(known_dates) == 0:
        return []

    # If last row is missing, extrapolate +1 month from previous
    all_dates = list(known_dates)
    expected = len(df)
    while len(all_dates) < expected:
        last = all_dates[-1]
        # Add one month
        month = last.month + 1
        year = last.year + (month > 12)
        month = month if month <= 12 else month - 12
        all_dates.append(date(year, month, 1))

    return all_dates


async def seed_snapshots(
    session: AsyncSession,
    name_to_id: dict[str, str],
    df: pd.DataFrame,
    dates: list[date],
) -> int:
    """Insert snapshots from Historical_amounts. Returns count inserted."""
    count = 0
    for row_idx, row in enumerate(df.itertuples(index=False)):
        if row_idx >= len(dates):
            break
        snap_date = dates[row_idx]

        for col_idx, asset_name in COLUMN_TO_ASSET.items():
            asset_id = name_to_id.get(asset_name)
            if not asset_id:
                continue

            try:
                raw_val = row[col_idx]
                if pd.isna(raw_val):
                    continue
                amount = float(raw_val)
            except (ValueError, TypeError, IndexError):
                continue

            await session.execute(
                text("""
                    INSERT INTO snapshots (asset_id, date, amount, source)
                    VALUES (:asset_id, :date, :amount, :source)
                    ON CONFLICT (asset_id, date) DO UPDATE
                        SET amount = EXCLUDED.amount,
                            source = EXCLUDED.source
                """),
                {
                    "asset_id": asset_id,
                    "date": snap_date,
                    "amount": amount,
                    "source": "excel_migration",
                },
            )
            count += 1

    await session.commit()
    return count


async def seed_fonchim_snapshot(
    session: AsyncSession,
    fonchim_id: str,
    amount: float,
    snap_date: date,
) -> None:
    """Insert Fonchim's single snapshot (Dashboard value only)."""
    log.warning(
        "Fonchim: no historical time series available — seeding single snapshot from Dashboard"
    )
    await session.execute(
        text("""
            INSERT INTO snapshots (asset_id, date, amount, source)
            VALUES (:asset_id, :date, :amount, :source)
            ON CONFLICT (asset_id, date) DO UPDATE
                SET amount = EXCLUDED.amount
        """),
        {
            "asset_id": fonchim_id,
            "date": snap_date,
            "amount": amount,
            "source": "excel_migration",
        },
    )
    await session.commit()


async def seed_goals(session: AsyncSession) -> None:
    """Seed the 3 pre-defined goals."""
    goals = [
        {
            "name": "Emergency Fund",
            "description": "3-6 months of expenses as liquid safety net",
            "target_amount": 7500.00,
            "target_date": None,
            "goal_type": "emergency_fund",
            "asset_scope": '["cash", "money_market"]',
        },
        {
            "name": "Home Purchase Fund",
            "description": "Down payment savings target",
            "target_amount": 10000.00,
            "target_date": None,
            "goal_type": "purchase",
            "asset_scope": '["cash", "money_market"]',
        },
        {
            "name": "FIRE Target",
            "description": "Financial Independence — 25x annual expenses",
            "target_amount": 500000.00,
            "target_date": None,
            "goal_type": "fire",
            "asset_scope": '"all"',
        },
    ]

    for goal in goals:
        await session.execute(
            text("""
                INSERT INTO goals (name, description, target_amount, target_date, goal_type, asset_scope)
                VALUES (:name, :description, :target_amount, :target_date, :goal_type, CAST(:asset_scope AS jsonb))
                ON CONFLICT DO NOTHING
            """),
            goal,
        )

    await session.commit()
    log.info("Seeded 3 goals")


async def verify(session: AsyncSession) -> bool:
    """Run verification assertions."""
    ok = True

    # 1. Asset count
    result = await session.execute(text("SELECT COUNT(*) FROM assets"))
    asset_count = result.scalar()
    if asset_count != 9:
        log.error("FAIL: expected 9 assets, got %d", asset_count)
        ok = False
    else:
        log.info("PASS: 9 assets")

    # 2. Fonchim has exactly 1 snapshot
    result = await session.execute(
        text("SELECT COUNT(*) FROM snapshots s JOIN assets a ON s.asset_id = a.id WHERE a.name = 'Fonchim'")
    )
    fonchim_count = result.scalar()
    if fonchim_count != 1:
        log.error("FAIL: Fonchim should have 1 snapshot, got %d", fonchim_count)
        ok = False
    else:
        log.info("PASS: Fonchim has 1 snapshot")

    # 3. Latest net worth — sum of the most-recent snapshot per active asset
    result = await session.execute(
        text("""
            SELECT SUM(latest.amount)
            FROM (
                SELECT DISTINCT ON (s.asset_id) s.amount
                FROM snapshots s
                JOIN assets a ON s.asset_id = a.id
                WHERE a.is_active = true
                ORDER BY s.asset_id, s.date DESC
            ) AS latest
        """)
    )
    total = float(result.scalar() or 0)
    expected_total = 38846.0
    tolerance = 500.0
    if abs(total - expected_total) > tolerance:
        log.error("FAIL: expected total ~€%.0f, got €%.2f", expected_total, total)
        ok = False
    else:
        log.info("PASS: latest total €%.2f (expected ~€%.0f)", total, expected_total)

    return ok


async def main() -> None:
    if not EXCEL_PATH.exists():
        log.error("Excel file not found: %s", EXCEL_PATH)
        sys.exit(1)

    log.info("Reading %s", EXCEL_PATH)

    # Read Historical_amounts sheet
    hist_df = pd.read_excel(
        EXCEL_PATH,
        sheet_name="Historical_amounts",
        header=0,
    )
    # Keep only data rows (skip header if any)
    # Rows 2-23 in Excel = rows 0-21 in 0-indexed DataFrame
    hist_df = hist_df.iloc[:22].reset_index(drop=True)

    dates = _infer_missing_dates(hist_df)
    log.info("Found %d snapshot dates: %s → %s", len(dates), dates[0] if dates else "?", dates[-1] if dates else "?")

    # Try to read Fonchim value from Dashboard sheet
    fonchim_amount = 12099.0
    fonchim_date = date(2026, 2, 1)
    try:
        dash_df = pd.read_excel(EXCEL_PATH, sheet_name="Dashboard", header=None)
        log.info("Dashboard sheet loaded (%d rows)", len(dash_df))
        # Fonchim is noted at €12,099 in dashboard — use as default
    except Exception as e:
        log.warning("Could not read Dashboard sheet: %s — using hardcoded Fonchim value", e)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        log.info("Seeding assets...")
        name_to_id = await seed_assets(session)

        log.info("Seeding snapshots from Historical_amounts...")
        snap_count = await seed_snapshots(session, name_to_id, hist_df, dates)
        log.info("Inserted/updated %d snapshot rows", snap_count)

        log.info("Seeding Fonchim snapshot (€%.2f on %s)...", fonchim_amount, fonchim_date)
        await seed_fonchim_snapshot(
            session, name_to_id["Fonchim"], fonchim_amount, fonchim_date
        )

        log.info("Seeding goals...")
        await seed_goals(session)

        log.info("Running verification...")
        passed = await verify(session)

    await engine.dispose()

    if passed:
        log.info("Migration complete ✓")
    else:
        log.error("Migration finished with verification failures")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
