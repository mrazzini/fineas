"""Shared CSV loader for assets + snapshots.

Used by both the one-shot `scripts/seed.py` (owner='demo') and the HTTP
`POST /data/load` endpoint (owner='real').  Idempotent: assets upsert on
(owner, name), snapshots upsert on (asset_id, snapshot_date).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Asset, AssetSnapshot, AssetType


ASSET_TYPE_MAP = {t.value: t for t in AssetType}


@dataclass
class LoadResult:
    assets_inserted: int = 0
    assets_updated: int = 0
    snapshots_inserted: int = 0
    snapshots_updated: int = 0
    skipped: list[str] = field(default_factory=list)


def _parse_assets_rows(rows: Iterable[dict]) -> list[dict]:
    parsed: list[dict] = []
    for i, row in enumerate(rows, start=1):
        try:
            name = row["name"].strip()
            asset_type = ASSET_TYPE_MAP[row["asset_type"].strip()]
            ret = row.get("annualized_return_pct", "").strip()
            parsed.append({
                "name": name,
                "asset_type": asset_type,
                "annualized_return_pct": Decimal(ret) if ret else None,
            })
        except (KeyError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"Invalid assets row {i}: {exc}") from exc
    return parsed


def _parse_snapshots_rows(rows: Iterable[dict]) -> list[dict]:
    parsed: list[dict] = []
    for i, row in enumerate(rows, start=1):
        try:
            asset_name = row["asset_name"].strip()
            day, month, year = row["snapshot_date"].strip().split("/")
            snap_date = date(int(year), int(month), int(day))
            balance = Decimal(row["balance"].strip())
            parsed.append({
                "asset_name": asset_name,
                "snapshot_date": snap_date,
                "balance": balance,
            })
        except (KeyError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"Invalid snapshots row {i}: {exc}") from exc
    return parsed


def parse_csv_text(text: str) -> list[dict]:
    """Parse CSV text into a list of row dicts (all values as strings)."""
    reader = csv.DictReader(StringIO(text), skipinitialspace=True)
    return list(reader)


async def load_portfolio(
    session: AsyncSession,
    assets_rows: list[dict],
    snapshots_rows: list[dict],
    owner: str,
) -> LoadResult:
    """Upsert assets and snapshots for the given owner in one transaction.

    assets_rows: dicts with keys name, asset_type, annualized_return_pct.
    snapshots_rows: dicts with keys asset_name, snapshot_date (DD/MM/YYYY), balance.
    """
    result = LoadResult()
    parsed_assets = _parse_assets_rows(assets_rows)
    parsed_snapshots = _parse_snapshots_rows(snapshots_rows)

    for asset in parsed_assets:
        stmt = (
            pg_insert(Asset)
            .values(owner=owner, **asset)
            .on_conflict_do_update(
                constraint="uq_asset_owner_name",
                set_={
                    "asset_type": asset["asset_type"],
                    "annualized_return_pct": asset["annualized_return_pct"],
                },
            )
        )
        res = await session.execute(stmt)
        # rowcount is 1 for both insert and update with on_conflict_do_update;
        # we differentiate by checking existence first would require a round-trip,
        # so we lump both as "inserted" for the seed use-case. The endpoint
        # reports a total count rather than insert-vs-update breakdown.
        if res.rowcount:
            result.assets_inserted += 1

    id_result = await session.execute(
        select(Asset.id, Asset.name).where(Asset.owner == owner)
    )
    asset_ids = {name: uid for uid, name in id_result.all()}

    for snap in parsed_snapshots:
        asset_id = asset_ids.get(snap["asset_name"])
        if asset_id is None:
            result.skipped.append(
                f"Unknown asset '{snap['asset_name']}' on {snap['snapshot_date']}"
            )
            continue
        stmt = (
            pg_insert(AssetSnapshot)
            .values(
                asset_id=asset_id,
                owner=owner,
                snapshot_date=snap["snapshot_date"],
                balance=snap["balance"],
            )
            .on_conflict_do_update(
                constraint="uq_snapshot_asset_date",
                set_={"balance": snap["balance"]},
            )
        )
        res = await session.execute(stmt)
        if res.rowcount:
            result.snapshots_inserted += 1

    await session.commit()
    return result
