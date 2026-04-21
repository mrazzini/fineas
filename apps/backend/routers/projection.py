"""Stateless FIRE-projection endpoint.

Pure compute — no DB read, no auth. The caller supplies the current asset
balances; the server runs `project_portfolio()` and returns the projection.
Usable by anonymous demo visitors (frontend sends the demo fixture) and by
the authenticated owner (frontend sends data fetched from /assets).
"""
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from projection import AssetInput, project_portfolio
from schemas import ProjectionResponse

router = APIRouter(prefix="/projection", tags=["projection"])


class ProjectionAssetIn(BaseModel):
    asset_id: uuid.UUID
    name: str
    current_balance: Decimal
    annualized_return_pct: Decimal = Decimal("0")


class ProjectionRequest(BaseModel):
    assets: list[ProjectionAssetIn] = Field(default_factory=list)
    months: int = 120
    monthly_contribution: Decimal = Decimal("0")
    annual_expenses: Optional[Decimal] = None
    safe_withdrawal_rate: float = 0.04


@router.post("/compute", response_model=ProjectionResponse)
async def compute_projection(payload: ProjectionRequest) -> ProjectionResponse:
    inputs = [
        AssetInput(
            asset_id=a.asset_id,
            name=a.name,
            current_balance=a.current_balance,
            annualized_return_pct=a.annualized_return_pct,
        )
        for a in payload.assets
    ]

    result = project_portfolio(
        assets=inputs,
        months=payload.months,
        monthly_contribution=payload.monthly_contribution,
        annual_expenses=payload.annual_expenses,
        safe_withdrawal_rate=payload.safe_withdrawal_rate,
    )

    return ProjectionResponse(
        current_total=result.current_total,
        fire_target=result.fire_target,
        fire_date=result.fire_date,
        months_to_fire=result.months_to_fire,
        asset_summaries=[
            {
                "asset_id": s.asset_id,
                "name": s.name,
                "current_balance": s.current_balance,
                "projected_balance": s.projected_balance,
            }
            for s in result.asset_summaries
        ],
        monthly=[
            {
                "month": m.month,
                "date": m.date,
                "portfolio_total": m.portfolio_total,
                "asset_balances": m.asset_balances,
            }
            for m in result.monthly
        ],
    )
