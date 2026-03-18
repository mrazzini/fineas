"""
CRUD endpoints for AssetSnapshot, nested under /assets/{asset_id}.

Route summary:
  POST  /assets/{id}/snapshots  -> 201 SnapshotRead | 404 | 409
  GET   /assets/{id}/snapshots  -> 200 list[SnapshotRead] | 404
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AssetSnapshot
from routers.deps import get_asset_or_404
from schemas import SnapshotCreate, SnapshotRead

router = APIRouter(prefix="/assets/{asset_id}/snapshots", tags=["snapshots"])


@router.post("", response_model=SnapshotRead, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    asset_id: uuid.UUID,
    payload: SnapshotCreate,
    db: AsyncSession = Depends(get_db),
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
async def list_snapshots(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await get_asset_or_404(asset_id, db)
    result = await db.execute(
        select(AssetSnapshot)
        .where(AssetSnapshot.asset_id == asset_id)
        .order_by(AssetSnapshot.snapshot_date)
    )
    return result.scalars().all()
