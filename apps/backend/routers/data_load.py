"""Password-gated bulk CSV loader for real portfolio data.

Route:
  POST /data/load  (multipart: assets + snapshots files)  -> 200 LoadSummary
"""
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import config
from auth import require_owner
from database import get_db
from services.loader import load_portfolio, parse_csv_text

router = APIRouter(prefix="/data", tags=["data"])


class LoadSummary(BaseModel):
    assets_loaded: int
    snapshots_loaded: int
    skipped: list[str]


async def _read_csv_upload(file: UploadFile, label: str) -> list[dict]:
    raw = await file.read()
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{label} file exceeds {config.MAX_UPLOAD_BYTES} bytes.",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} file must be UTF-8 encoded CSV.",
        ) from exc
    return parse_csv_text(text)


@router.post("/load", response_model=LoadSummary)
async def load_real_data(
    assets: UploadFile = File(...),
    snapshots: UploadFile = File(...),
    _: bool = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> LoadSummary:
    """Upsert real portfolio data (owner='real') from two CSV uploads.

    Expected schemas match `data/example_*.csv`:
      - assets:    name, asset_type, annualized_return_pct
      - snapshots: asset_name, snapshot_date (DD/MM/YYYY), balance
    """
    assets_rows = await _read_csv_upload(assets, "assets")
    snapshots_rows = await _read_csv_upload(snapshots, "snapshots")

    try:
        result = await load_portfolio(
            db,
            assets_rows=assets_rows,
            snapshots_rows=snapshots_rows,
            owner="real",
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return LoadSummary(
        assets_loaded=result.assets_inserted,
        snapshots_loaded=result.snapshots_inserted,
        skipped=result.skipped,
    )
