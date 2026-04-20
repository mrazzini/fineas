"""Password-gated bulk loader for real portfolio data.

Route:
  POST /data/load  (JSON: assets + snapshots, pre-mapped by the client) -> 200
"""
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_owner
from database import get_db
from models import AssetType
from services.loader import load_portfolio

router = APIRouter(prefix="/data", tags=["data"])


class AssetEntry(BaseModel):
    """One asset row, already mapped by the user on the /load-data UI."""
    original_name: Annotated[str, Field(min_length=1, max_length=100)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    asset_type: AssetType
    annualized_return_pct: Decimal | None = None


class SnapshotEntry(BaseModel):
    asset_name: Annotated[str, Field(min_length=1, max_length=100)]
    snapshot_date: str  # DD/MM/YYYY — matches example CSV format
    balance: Decimal


class LoadRequest(BaseModel):
    assets: list[AssetEntry]
    snapshots: list[SnapshotEntry]


class LoadSummary(BaseModel):
    assets_loaded: int
    snapshots_loaded: int
    skipped: list[str]


@router.post("/load", response_model=LoadSummary)
async def load_real_data(
    payload: LoadRequest,
    _: bool = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> LoadSummary:
    """Upsert real portfolio data (owner='real') from the UI's mapped payload."""
    rename = {a.original_name: a.name for a in payload.assets if a.original_name != a.name}

    assets_rows = [
        {
            "name": a.name,
            "asset_type": a.asset_type.value,
            "annualized_return_pct": str(a.annualized_return_pct)
            if a.annualized_return_pct is not None
            else "",
        }
        for a in payload.assets
    ]
    snapshots_rows = [
        {
            "asset_name": rename.get(s.asset_name, s.asset_name),
            "snapshot_date": s.snapshot_date,
            "balance": str(s.balance),
        }
        for s in payload.snapshots
    ]

    try:
        result = await load_portfolio(
            db, assets_rows=assets_rows, snapshots_rows=snapshots_rows, owner="real"
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return LoadSummary(
        assets_loaded=result.assets_inserted,
        snapshots_loaded=result.snapshots_inserted,
        skipped=result.skipped,
    )
