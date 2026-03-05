import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetBase(BaseModel):
    name: str
    asset_type: str
    platform: str | None = None
    expected_annual_return: float | None = None
    is_active: bool = True
    metadata_: dict = {}

    model_config = ConfigDict(populate_by_name=True)


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: str | None = None
    asset_type: str | None = None
    platform: str | None = None
    expected_annual_return: float | None = None
    is_active: bool | None = None
    metadata_: dict | None = None


class AssetResponse(AssetBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
