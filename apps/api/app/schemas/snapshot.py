import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SnapshotBase(BaseModel):
    asset_id: uuid.UUID
    date: date
    amount: float
    source: str = "manual"


class SnapshotCreate(BaseModel):
    asset_id: uuid.UUID
    date: date
    amount: float
    source: str = "manual"


class SnapshotUpdate(BaseModel):
    amount: float | None = None
    source: str | None = None


class SnapshotResponse(SnapshotBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HoldingInfo(BaseModel):
    asset_id: uuid.UUID
    asset_name: str
    asset_type: str
    platform: str | None
    current_amount: float
    snapshot_date: date
    allocation_pct: float = 0.0
    change_since_last: float = 0.0
    change_pct: float = 0.0


class PortfolioSummary(BaseModel):
    total_net_worth: float
    holdings: list[HoldingInfo]
    as_of_date: date


class NetWorthHistory(BaseModel):
    date: date
    total: float
