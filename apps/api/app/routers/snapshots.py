import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.asset import Asset
from app.models.snapshot import Snapshot
from app.schemas.snapshot import (
    HoldingInfo,
    NetWorthHistory,
    PortfolioSummary,
    SnapshotCreate,
    SnapshotResponse,
)

router = APIRouter()


@router.get("/latest", response_model=PortfolioSummary)
async def get_latest_snapshots(
    session: AsyncSession = Depends(get_session),
) -> PortfolioSummary:
    """Latest snapshot per active asset — dashboard view."""
    # DISTINCT ON (asset_id) ordered by date DESC gives latest per asset
    latest_stmt = (
        select(Snapshot)
        .join(Asset, Snapshot.asset_id == Asset.id)
        .where(Asset.is_active.is_(True))
        .distinct(Snapshot.asset_id)
        .order_by(Snapshot.asset_id, Snapshot.date.desc())
    )
    result = await session.execute(latest_stmt)
    latest_snapshots = list(result.scalars().all())

    total = sum(s.amount for s in latest_snapshots)
    as_of = max((s.date for s in latest_snapshots), default=date.today())

    # Get previous snapshot per asset for delta calculation
    holdings = []
    for snap in latest_snapshots:
        asset = await session.get(Asset, snap.asset_id)
        if not asset:
            continue

        # Find previous snapshot for this asset
        prev_stmt = (
            select(Snapshot)
            .where(Snapshot.asset_id == snap.asset_id)
            .where(Snapshot.date < snap.date)
            .order_by(Snapshot.date.desc())
            .limit(1)
        )
        prev_result = await session.execute(prev_stmt)
        prev = prev_result.scalar_one_or_none()

        change = float(snap.amount) - float(prev.amount) if prev else 0.0
        change_pct = (change / float(prev.amount) * 100) if prev and prev.amount else 0.0

        holdings.append(
            HoldingInfo(
                asset_id=snap.asset_id,
                asset_name=asset.name,
                asset_type=asset.asset_type,
                platform=asset.platform,
                current_amount=float(snap.amount),
                snapshot_date=snap.date,
                allocation_pct=round(float(snap.amount) / total * 100, 2) if total else 0.0,
                change_since_last=round(change, 2),
                change_pct=round(change_pct, 2),
            )
        )

    return PortfolioSummary(total_net_worth=round(total, 2), holdings=holdings, as_of_date=as_of)


@router.get("/history", response_model=list[NetWorthHistory])
async def get_net_worth_history(
    session: AsyncSession = Depends(get_session),
) -> list[NetWorthHistory]:
    """Net worth time series grouped by date."""
    stmt = (
        select(Snapshot.date, func.sum(Snapshot.amount).label("total"))
        .join(Asset, Snapshot.asset_id == Asset.id)
        .where(Asset.is_active.is_(True))
        .group_by(Snapshot.date)
        .order_by(Snapshot.date)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [NetWorthHistory(date=row.date, total=float(row.total)) for row in rows]


@router.get("/", response_model=list[SnapshotResponse])
async def list_snapshots(
    asset_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Snapshot]:
    stmt = select(Snapshot).order_by(Snapshot.date.desc())
    if asset_id:
        stmt = stmt.where(Snapshot.asset_id == asset_id)
    if from_date:
        stmt = stmt.where(Snapshot.date >= from_date)
    if to_date:
        stmt = stmt.where(Snapshot.date <= to_date)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=SnapshotResponse, status_code=201)
async def create_snapshot(
    payload: SnapshotCreate,
    session: AsyncSession = Depends(get_session),
) -> Snapshot:
    # Upsert: if (asset_id, date) exists, update amount
    stmt = (
        select(Snapshot)
        .where(Snapshot.asset_id == payload.asset_id)
        .where(Snapshot.date == payload.date)
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.amount = payload.amount
        existing.source = payload.source
        await session.commit()
        await session.refresh(existing)
        return existing

    snap = Snapshot(
        asset_id=payload.asset_id,
        date=payload.date,
        amount=payload.amount,
        source=payload.source,
    )
    session.add(snap)
    await session.commit()
    await session.refresh(snap)
    return snap
