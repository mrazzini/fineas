"""
Deterministic FIRE projection engine — pure Python, zero DB or HTTP calls.

Design principles:
  - All inputs are explicit parameters; callers own DB queries.
  - Uses Decimal throughout for monetary precision.
  - annualized_return_pct stored on each Asset drives growth; no LLM/ML involved.
  - Monthly contribution is treated as a lump sum invested at the start of each
    month and growing at the portfolio blended rate (weighted by current balances).

FIRE math:
  - FIRE target  = annual_expenses / safe_withdrawal_rate  (4% rule → 25x)
  - FV per asset = balance * (1 + r_monthly)^n
  - Contribution pool FV = C * ((1+r)^n - 1) / r   [annuity formula]
                         = C * n                     [when r == 0]
  - Fire date    = first month where portfolio_total >= fire_target
"""

import calendar
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

TWO_PLACES = Decimal("0.01")


def _add_months(d: date, n: int) -> date:
    """Add n months to a date, clamping to the last day of the target month."""
    total_months = d.month - 1 + n
    year = d.year + total_months // 12
    month = total_months % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


@dataclass
class AssetInput:
    """Snapshot of a single asset handed to the projection engine."""
    asset_id: uuid.UUID
    name: str
    current_balance: Decimal
    annualized_return_pct: Decimal  # e.g. Decimal("0.085")


@dataclass
class AssetProjectionPoint:
    asset_id: uuid.UUID
    name: str
    current_balance: Decimal
    projected_balance: Decimal  # balance at end of projection window


@dataclass
class MonthlySlice:
    month: int          # 1-indexed: month 1 = one month from start_date
    date: date
    portfolio_total: Decimal
    # Keyed by str(asset_id); contributions not broken out per-asset
    asset_balances: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class ProjectionResult:
    current_total: Decimal
    fire_target: Optional[Decimal]      # None when annual_expenses not provided
    fire_date: Optional[date]           # None when target not reached in window
    months_to_fire: Optional[int]
    asset_summaries: list[AssetProjectionPoint]
    monthly: list[MonthlySlice]


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _monthly_rate(annualized: Decimal) -> Decimal:
    """Convert an annualized return percentage to a monthly multiplier."""
    return annualized / Decimal("12")


def _fv_lump_sum(principal: Decimal, monthly_rate: Decimal, n: int) -> Decimal:
    """Future value of a lump sum after n monthly compounding periods."""
    if monthly_rate == Decimal("0") or principal == Decimal("0"):
        return principal
    return principal * (1 + monthly_rate) ** n


def _fv_annuity(payment: Decimal, monthly_rate: Decimal, n: int) -> Decimal:
    """
    Future value of an ordinary annuity (payment at start of each period).
    payment * ((1+r)^n - 1) / r  when r > 0
    payment * n                  when r == 0
    """
    if payment == Decimal("0"):
        return Decimal("0")
    if monthly_rate == Decimal("0"):
        return payment * n
    return payment * ((1 + monthly_rate) ** n - 1) / monthly_rate


def _blended_monthly_rate(assets: list[AssetInput]) -> Decimal:
    """
    Weighted-average monthly rate across all assets.
    Used to compound the monthly contribution pool.
    Zero-balance assets are excluded from the weight so they don't dilute the rate.
    Falls back to simple average if total balance is zero.
    """
    total_balance = sum(a.current_balance for a in assets)
    if total_balance == Decimal("0"):
        # No history yet — use simple average of stored rates
        rates = [_monthly_rate(a.annualized_return_pct) for a in assets]
        if not rates:
            return Decimal("0")
        return sum(rates) / len(rates)
    return sum(
        _monthly_rate(a.annualized_return_pct) * a.current_balance for a in assets
    ) / total_balance


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def project_portfolio(
    assets: list[AssetInput],
    months: int = 120,
    monthly_contribution: Decimal = Decimal("0"),
    annual_expenses: Optional[Decimal] = None,
    safe_withdrawal_rate: float = 0.04,
    start_date: Optional[date] = None,
) -> ProjectionResult:
    """
    Project portfolio growth forward `months` periods.

    Args:
        assets:               List of AssetInput (asset definition + current balance).
        months:               Number of monthly periods to project.
        monthly_contribution: New money added to the portfolio each month.
        annual_expenses:      Target annual spending in retirement (for FIRE calc).
        safe_withdrawal_rate: Fraction of portfolio withdrawn per year (default 4%).
        start_date:           Projection start; defaults to today.

    Returns:
        ProjectionResult with per-asset summaries, monthly timeline, and FIRE info.
    """
    if start_date is None:
        start_date = date.today()

    swr = Decimal(str(safe_withdrawal_rate))
    fire_target: Optional[Decimal] = (
        (annual_expenses / swr).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if annual_expenses is not None
        else None
    )

    current_total = sum((a.current_balance for a in assets), Decimal("0"))
    blended_rate = _blended_monthly_rate(assets)

    monthly_slices: list[MonthlySlice] = []
    fire_date: Optional[date] = None
    months_to_fire: Optional[int] = None

    for n in range(1, months + 1):
        slice_date = _add_months(start_date, n)

        asset_balances: dict[str, Decimal] = {}
        asset_total = Decimal("0")
        for a in assets:
            r = _monthly_rate(a.annualized_return_pct)
            bal = _fv_lump_sum(a.current_balance, r, n).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
            asset_balances[str(a.asset_id)] = bal
            asset_total += bal

        contribution_pool = _fv_annuity(
            monthly_contribution, blended_rate, n
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        portfolio_total = (asset_total + contribution_pool).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

        monthly_slices.append(
            MonthlySlice(
                month=n,
                date=slice_date,
                portfolio_total=portfolio_total,
                asset_balances=asset_balances,
            )
        )

        if fire_target is not None and fire_date is None and portfolio_total >= fire_target:
            fire_date = slice_date
            months_to_fire = n

    # Per-asset end-of-window summary
    asset_summaries = [
        AssetProjectionPoint(
            asset_id=a.asset_id,
            name=a.name,
            current_balance=a.current_balance,
            projected_balance=monthly_slices[-1].asset_balances[str(a.asset_id)]
            if monthly_slices
            else a.current_balance,
        )
        for a in assets
    ]

    return ProjectionResult(
        current_total=current_total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        fire_target=fire_target,
        fire_date=fire_date,
        months_to_fire=months_to_fire,
        asset_summaries=asset_summaries,
        monthly=monthly_slices,
    )
