"""Shared FastAPI dependencies used by multiple routers."""
import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import current_owner, owner_scope
from models import Asset


def get_owner_scope(is_authed: bool = Depends(current_owner)) -> str:
    """Read-path dependency: 'real' for authed callers, 'demo' otherwise."""
    return owner_scope(is_authed)


async def get_asset_or_404(
    asset_id: uuid.UUID, db: AsyncSession, scope: str | None = None
) -> Asset:
    """Fetch an Asset by id, optionally restricted to a given owner scope.

    Cross-scope access returns 404 (not 403) so that demo-scope callers
    can't enumerate which real-asset ids exist.
    """
    q = select(Asset).where(Asset.id == asset_id)
    if scope is not None:
        q = q.where(Asset.owner == scope)
    result = await db.execute(q)
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset
