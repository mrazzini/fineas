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


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------


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
    is_archived: Optional[bool] = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    asset_type: AssetType
    annualized_return_pct: Optional[Decimal] = None
    ticker: Optional[str] = None
    is_archived: bool
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


# ---------------------------------------------------------------------------
# Projection / FIRE schemas
# ---------------------------------------------------------------------------

class AssetProjectionSchema(BaseModel):
    """Per-asset summary: where it starts and where it ends up."""
    asset_id: uuid.UUID
    name: str
    current_balance: Decimal
    projected_balance: Decimal


class MonthlySliceSchema(BaseModel):
    """Portfolio state at one point in the projection timeline."""
    month: int          # 1-indexed
    date: date
    portfolio_total: Decimal
    # str(UUID) → balance; contributions are not shown per-asset
    asset_balances: dict[str, Decimal]


class ProjectionResponse(BaseModel):
    current_total: Decimal
    fire_target: Optional[Decimal] = None      # None when annual_expenses not supplied
    fire_date: Optional[date] = None           # None when target not reached in window
    months_to_fire: Optional[int] = None
    asset_summaries: list[AssetProjectionSchema]
    monthly: list[MonthlySliceSchema]


# ---------------------------------------------------------------------------
# Ingestion schemas (Phase 3)
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    """Free-form text or pasted CSV to parse into structured portfolio data."""
    text: str


class IngestResponse(BaseModel):
    """
    Result of the LangGraph ingestion pipeline.

    The endpoint is parse-only — no DB writes happen here.  The caller uses
    validated_assets / validated_snapshots to drive subsequent upsert calls,
    or waits for the Phase 4 HITL agent to do it automatically.
    """
    parsed_assets: list[dict]        # raw LLM output before validation
    parsed_snapshots: list[dict]     # raw LLM output before validation
    validated_assets: list[dict]     # items that passed all validation rules
    validated_snapshots: list[dict]  # items that passed all validation rules
    validation_errors: list[str]     # human-readable descriptions of problems
    is_valid: bool                   # True when validation_errors is empty


# ---------------------------------------------------------------------------
# Apply schemas (Phase 4 — HITL)
# ---------------------------------------------------------------------------


class ApplyRequest(BaseModel):
    """Human-approved data to write to the database in one transaction."""
    validated_assets: list[dict]
    validated_snapshots: list[dict]


class ApplyResponse(BaseModel):
    """Result of the apply step — what was written and any per-item errors."""
    applied_assets: list[dict]
    applied_snapshots: list[dict]
    apply_errors: list[str]
    success: bool