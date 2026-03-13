"""
Pydantic v2 schemas — the HTTP contract layer between FastAPI and the ORM.

Three schema families:
  - AssetCreate / AssetUpdate / AssetRead
  - SnapshotCreate / SnapshotRead

The *Read schemas use `model_config = ConfigDict(from_attributes=True)` which
tells Pydantic to read values from ORM object attributes (not just dicts).
This is the Pydantic v2 replacement for orm_mode = True.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from models import AssetType


class AssetCreate(BaseModel):
    name: str
    asset_type: AssetType
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None


class AssetUpdate(BaseModel):
    """All fields optional — supports partial PATCH updates."""
    name: Optional[str] = None
    asset_type: Optional[AssetType] = None
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    asset_type: AssetType
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None
    created_at: datetime


class SnapshotCreate(BaseModel):
    snapshot_date: date
    balance: Decimal


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    snapshot_date: date
    balance: Decimal
    created_at: datetime