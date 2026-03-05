"""
Deterministic compound growth FIRE projection.

Formula: FV(t) = PV * (1+r)^t + C * [((1+r)^t - 1) / r]
where:
  PV = current portfolio value
  r  = weighted_real_return (monthly)
  C  = monthly_contribution
  t  = months

Return assumptions (real, inflation-adjusted) per asset class:
  TODO Phase 2+: replace inflation_rate with live fetch from ECB SDW or FRED API
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.snapshot import Snapshot
from app.schemas.projection import CompoundParams, CompoundResult, CompoundYearlyPoint

# Real (inflation-adjusted) annual returns by asset type
REAL_RETURNS: dict[str, float] = {
    "stocks": 0.06,
    "bonds": 0.015,
    "money_market": 0.015,
    "p2p_lending": 0.08,
    "pension": 0.042,
    "cash": 0.00,
}

DEFAULT_INFLATION_RATE = 0.02  # ECB 20-year average; not configurable via env by design


async def _get_current_portfolio(session: AsyncSession) -> tuple[float, dict[str, float]]:
    """Returns (total_value, {asset_type: value}) from latest snapshots."""
    # Latest snapshot per active asset
    latest_stmt = (
        select(Snapshot)
        .join(Asset, Snapshot.asset_id == Asset.id)
        .where(Asset.is_active.is_(True))
        .distinct(Snapshot.asset_id)
        .order_by(Snapshot.asset_id, Snapshot.date.desc())
    )
    result = await session.execute(latest_stmt)
    snapshots = list(result.scalars().all())

    type_values: dict[str, float] = {}
    for snap in snapshots:
        asset = await session.get(Asset, snap.asset_id)
        if asset:
            type_values[asset.asset_type] = type_values.get(asset.asset_type, 0.0) + float(
                snap.amount
            )

    total = sum(type_values.values())
    return total, type_values


def _compute_weighted_return(type_values: dict[str, float], total: float) -> float:
    """Compute allocation-weighted real annual return."""
    if total == 0:
        return REAL_RETURNS["stocks"]

    weighted = 0.0
    for asset_type, value in type_values.items():
        r = REAL_RETURNS.get(asset_type, 0.05)
        weighted += r * (value / total)
    return weighted


async def run_compound_projection(
    params: CompoundParams, session: AsyncSession
) -> CompoundResult:
    """Run deterministic compound growth projection from current portfolio."""
    current_value, type_values = await _get_current_portfolio(session)

    weighted_annual_return = _compute_weighted_return(type_values, current_value)
    monthly_r = weighted_annual_return / 12

    pv = current_value
    c = params.monthly_contribution
    current_year = date.today().year

    trajectory: list[CompoundYearlyPoint] = []
    target_hit_year: int | None = None
    cumulative_contributions = 0.0

    for year_offset in range(1, params.horizon_years + 1):
        t = year_offset * 12  # months

        if monthly_r == 0:
            fv = pv + c * t
        else:
            fv = pv * (1 + monthly_r) ** t + c * (((1 + monthly_r) ** t - 1) / monthly_r)

        cumulative_contributions = c * t
        cumulative_returns = fv - pv - cumulative_contributions
        projection_year = current_year + year_offset

        trajectory.append(
            CompoundYearlyPoint(
                year=projection_year,
                projected_value=round(fv, 2),
                cumulative_contributions=round(cumulative_contributions, 2),
                cumulative_returns=round(cumulative_returns, 2),
            )
        )

        if (
            params.target_amount
            and target_hit_year is None
            and fv >= params.target_amount
        ):
            target_hit_year = projection_year

    final_value = trajectory[-1].projected_value if trajectory else current_value

    return CompoundResult(
        yearly_trajectory=trajectory,
        target_hit_year=target_hit_year,
        final_value_at_horizon=final_value,
        weighted_return=round(weighted_annual_return, 5),
    )
