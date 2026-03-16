# apps/backend/routers/assets.py
"""
CRUD endpoints for the Asset resource.

Route summary:
  POST   /assets            → 201 AssetRead
  GET    /assets            → 200 list[AssetRead]
  GET    /assets/{id}       → 200 AssetRead  | 404
  PATCH  /assets/{id}       → 200 AssetRead  | 404
  DELETE /assets/{id}       → 204            | 404
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Asset
from routers.deps import get_asset_or_404
from schemas import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with that name already exists.",
        )
    await db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetRead])
async def list_assets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).order_by(Asset.created_at))
    return result.scalars().all()


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await get_asset_or_404(asset_id, db)


@router.patch("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: uuid.UUID, payload: AssetUpdate, db: AsyncSession = Depends(get_db)
):
    asset = await get_asset_or_404(asset_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    asset = await get_asset_or_404(asset_id, db)
    await db.delete(asset)
    await db.commit()
