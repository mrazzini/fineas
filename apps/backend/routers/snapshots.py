"""
CRUD endpoints for AssetSnapshot, nested under /assets/{asset_id}.

All endpoints require authentication — public visitors use the demo fixture
served by the frontend.

Route summary:
  POST  /assets/{id}/snapshots         -> 201 SnapshotRead | 404 | 409
  GET   /assets/{id}/snapshots         -> 200 list[SnapshotRead] | 404
  POST  /assets/{id}/snapshots/upsert  -> 200 SnapshotRead | 404
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_owner
from database import get_db
from models import AssetSnapshot
from routers.deps import get_asset_or_404
from schemas import SnapshotCreate, SnapshotRead

router = APIRouter(
    prefix="/assets/{asset_id}/snapshots",
    tags=["snapshots"],
    dependencies=[Depends(require_owner)],
)


@router.post("", response_model=SnapshotRead, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    asset_id: uuid.UUID, payload: SnapshotCreate, db: AsyncSession = Depends(get_db)
):
    await get_asset_or_404(asset_id, db)
    snapshot = AssetSnapshot(asset_id=asset_id, **payload.model_dump())
    db.add(snapshot)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A snapshot for this asset on that date already exists.",
        )
    await db.refresh(snapshot)
    return snapshot


@router.get("", response_model=list[SnapshotRead])
async def list_snapshots(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await get_asset_or_404(asset_id, db)
    result = await db.execute(
        select(AssetSnapshot)
        .where(AssetSnapshot.asset_id == asset_id)
        .order_by(AssetSnapshot.snapshot_date)
    )
    return result.scalars().all()


@router.post("/upsert", response_model=SnapshotRead)
async def upsert_snapshot(
    asset_id: uuid.UUID, payload: SnapshotCreate, db: AsyncSession = Depends(get_db)
):
    """Insert or update a snapshot for the given asset + date."""
    await get_asset_or_404(asset_id, db)

    stmt = (
        pg_insert(AssetSnapshot)
        .values(
            asset_id=asset_id,
            snapshot_date=payload.snapshot_date,
            balance=payload.balance,
        )
        .on_conflict_do_update(
            constraint="uq_snapshot_asset_date",
            set_={"balance": payload.balance},
        )
        .returning(AssetSnapshot)
    )

    result = await db.execute(stmt)
    await db.commit()
    snapshot = result.scalar_one()
    return snapshot
