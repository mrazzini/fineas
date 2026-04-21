"""Shared FastAPI dependencies used by multiple routers."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Asset


async def get_asset_or_404(asset_id: uuid.UUID, db: AsyncSession) -> Asset:
    """Fetch an Asset by id, or raise 404."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset
