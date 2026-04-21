# apps/backend/routers/assets.py
"""
CRUD endpoints for the Asset resource.

Single-tenant model: every endpoint requires authentication. Public visitors
interact with a static demo fixture served by the frontend — not by this API.

Route summary:
  POST   /assets            -> 201 AssetRead        (auth)
  GET    /assets            -> 200 list[AssetRead]  (auth)
  GET    /assets/{id}       -> 200 AssetRead  | 404 (auth)
  PATCH  /assets/{id}       -> 200 AssetRead  | 404 (auth)
  DELETE /assets/{id}       -> 204            | 404 (auth)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_owner
from database import get_db
from models import Asset
from routers.deps import get_asset_or_404
from schemas import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[Depends(require_owner)],
)


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
async def list_assets(include_archived: bool = False, db: AsyncSession = Depends(get_db)):
    q = select(Asset).order_by(Asset.created_at)
    if not include_archived:
        q = q.where(Asset.is_archived == False)  # noqa: E712
    result = await db.execute(q)
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
