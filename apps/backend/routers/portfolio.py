"""
Portfolio-level projection endpoint.

Route summary:
  GET /portfolio/projection  → 200 ProjectionResponse

Query parameters:
  months               int     default 120  — projection horizon
  monthly_contribution Decimal default 0    — new money added each month
  annual_expenses      Decimal optional     — triggers FIRE date calculation
  safe_withdrawal_rate float   default 0.04 — fraction withdrawn per year (4% rule)

Logic:
  1. Fetch all non-archived assets.
  2. Get each asset's latest snapshot balance (0 if no snapshots yet).
  3. Delegate all math to projection.project_portfolio().
  4. Serialise and return.
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Asset, AssetSnapshot
from projection import AssetInput, project_portfolio
from routers.deps import get_owner_scope
from schemas import ProjectionResponse

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/projection", response_model=ProjectionResponse)
async def get_projection(
    months: int = 120,
    monthly_contribution: Decimal = Decimal("0"),
    annual_expenses: Optional[Decimal] = None,
    safe_withdrawal_rate: float = 0.04,
    db: AsyncSession = Depends(get_db),
    scope: str = Depends(get_owner_scope),
):
    # 1. Load all non-archived assets within the caller's owner scope
    result = await db.execute(
        select(Asset)
        .where(Asset.owner == scope)
        .where(Asset.is_archived == False)  # noqa: E712
        .order_by(Asset.created_at)
    )
    assets = result.scalars().all()

    # 2. Latest snapshot balance for each asset (subquery per asset)
    inputs: list[AssetInput] = []
    for asset in assets:
        latest = await db.execute(
            select(AssetSnapshot.balance)
            .where(AssetSnapshot.asset_id == asset.id)
            .order_by(AssetSnapshot.snapshot_date.desc())
            .limit(1)
        )
        balance_row = latest.scalar_one_or_none()
        current_balance = Decimal(str(balance_row)) if balance_row is not None else Decimal("0")

        inputs.append(
            AssetInput(
                asset_id=asset.id,
                name=asset.name,
                current_balance=current_balance,
                annualized_return_pct=Decimal(str(asset.annualized_return_pct or 0)),
            )
        )

    # 3. Run deterministic projection
    result_data = project_portfolio(
        assets=inputs,
        months=months,
        monthly_contribution=monthly_contribution,
        annual_expenses=annual_expenses,
        safe_withdrawal_rate=safe_withdrawal_rate,
    )

    # 4. Serialise to response schema
    return ProjectionResponse(
        current_total=result_data.current_total,
        fire_target=result_data.fire_target,
        fire_date=result_data.fire_date,
        months_to_fire=result_data.months_to_fire,
        asset_summaries=[
            {
                "asset_id": s.asset_id,
                "name": s.name,
                "current_balance": s.current_balance,
                "projected_balance": s.projected_balance,
            }
            for s in result_data.asset_summaries
        ],
        monthly=[
            {
                "month": m.month,
                "date": m.date,
                "portfolio_total": m.portfolio_total,
                "asset_balances": m.asset_balances,
            }
            for m in result_data.monthly
        ],
    )
