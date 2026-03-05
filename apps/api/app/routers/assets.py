import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate

router = APIRouter()


@router.get("/", response_model=list[AssetResponse])
async def list_assets(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[Asset]:
    stmt = select(Asset)
    if not include_inactive:
        stmt = stmt.where(Asset.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Asset:
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/", response_model=AssetResponse, status_code=201)
async def create_asset(
    payload: AssetCreate,
    session: AsyncSession = Depends(get_session),
) -> Asset:
    asset = Asset(
        name=payload.name,
        asset_type=payload.asset_type,
        platform=payload.platform,
        expected_annual_return=payload.expected_annual_return,
        is_active=payload.is_active,
        metadata_=payload.metadata_,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    session: AsyncSession = Depends(get_session),
) -> Asset:
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await session.commit()
    await session.refresh(asset)
    return asset
