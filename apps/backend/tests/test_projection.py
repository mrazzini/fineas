"""
Unit tests for the deterministic projection engine (projection.py).

These tests import projection.py directly — no DB, no HTTP, no fixtures needed.
Pure function in, pure data out.
"""

import uuid
from datetime import date
from decimal import Decimal

from projection import AssetInput, ProjectionResult, project_portfolio


def _asset(
    name: str = "Test",
    balance: str = "10000",
    rate: str = "0.08",
) -> AssetInput:
    return AssetInput(
        asset_id=uuid.uuid4(),
        name=name,
        current_balance=Decimal(balance),
        annualized_return_pct=Decimal(rate),
    )


# ---------------------------------------------------------------------------
# Basic growth
# ---------------------------------------------------------------------------

def test_zero_return_flat_balance():
    """An asset with 0% return should not grow."""
    a = _asset(balance="5000", rate="0.0")
    result = project_portfolio([a], months=12)
    assert result.monthly[11].asset_balances[str(a.asset_id)] == Decimal("5000.00")


def test_compound_growth_single_asset():
    """
    Verify FV formula: 10 000 at 12% annual (1% monthly) for 12 months.
    FV = 10000 * 1.01^12 ≈ 11268.25
    """
    a = _asset(balance="10000", rate="0.12")
    result = project_portfolio([a], months=12)
    fv = result.monthly[11].asset_balances[str(a.asset_id)]
    # Expect approximately 11268
    assert Decimal("11200") < fv < Decimal("11350")


def test_current_total_is_sum_of_balances():
    a1 = _asset(name="A", balance="10000", rate="0.08")
    a2 = _asset(name="B", balance="5000", rate="0.04")
    result = project_portfolio([a1, a2], months=12)
    assert result.current_total == Decimal("15000.00")


def test_multiple_assets_portfolio_total():
    """portfolio_total should equal sum of per-asset balances (no contributions)."""
    a1 = _asset(name="A", balance="10000", rate="0.08")
    a2 = _asset(name="B", balance="5000", rate="0.04")
    result = project_portfolio([a1, a2], months=6)
    for m in result.monthly:
        expected = sum(m.asset_balances.values())
        assert m.portfolio_total == expected


# ---------------------------------------------------------------------------
# Monthly contributions
# ---------------------------------------------------------------------------

def test_contribution_grows_portfolio():
    """Adding a monthly contribution should make totals larger than asset growth alone."""
    a = _asset(balance="10000", rate="0.06")
    no_contrib = project_portfolio([a], months=12, monthly_contribution=Decimal("0"))
    with_contrib = project_portfolio([a], months=12, monthly_contribution=Decimal("500"))
    assert with_contrib.monthly[-1].portfolio_total > no_contrib.monthly[-1].portfolio_total


def test_zero_balance_contribution_only():
    """Portfolio with zero-balance asset + contribution should accumulate contributions."""
    a = _asset(balance="0", rate="0.0")
    result = project_portfolio([a], months=3, monthly_contribution=Decimal("1000"))
    # 3 months × 1000 = 3000 (no compounding at 0% rate)
    assert result.monthly[2].portfolio_total == Decimal("3000.00")


# ---------------------------------------------------------------------------
# FIRE calculator
# ---------------------------------------------------------------------------

def test_fire_target_computed():
    """fire_target = annual_expenses / safe_withdrawal_rate."""
    a = _asset(balance="500000", rate="0.07")
    result = project_portfolio(
        [a], months=240, annual_expenses=Decimal("40000"), safe_withdrawal_rate=0.04
    )
    assert result.fire_target == Decimal("1000000.00")


def test_fire_date_found_within_window():
    """A large balance + high return should hit FIRE target before 240 months."""
    a = _asset(balance="800000", rate="0.08")
    result = project_portfolio(
        [a], months=240,
        monthly_contribution=Decimal("2000"),
        annual_expenses=Decimal("40000"),
        safe_withdrawal_rate=0.04,
    )
    assert result.fire_date is not None
    assert result.months_to_fire is not None
    assert 1 <= result.months_to_fire <= 240


def test_fire_date_null_when_not_reached():
    """A tiny balance should not reach a large FIRE target in a short window."""
    a = _asset(balance="100", rate="0.05")
    result = project_portfolio(
        [a], months=12,
        annual_expenses=Decimal("100000"),
        safe_withdrawal_rate=0.04,
    )
    assert result.fire_date is None
    assert result.months_to_fire is None


def test_fire_fields_null_without_expenses():
    """When annual_expenses is not supplied, all FIRE fields should be None."""
    a = _asset(balance="500000", rate="0.08")
    result = project_portfolio([a], months=60)
    assert result.fire_target is None
    assert result.fire_date is None
    assert result.months_to_fire is None


# ---------------------------------------------------------------------------
# Asset summaries
# ---------------------------------------------------------------------------

def test_asset_summaries_count_matches_inputs():
    assets = [_asset(name=f"A{i}") for i in range(5)]
    result = project_portfolio(assets, months=24)
    assert len(result.asset_summaries) == 5


def test_asset_summary_projected_balance_greater_than_current():
    """Positive return → projected_balance > current_balance."""
    a = _asset(balance="10000", rate="0.10")
    result = project_portfolio([a], months=12)
    summary = result.asset_summaries[0]
    assert summary.projected_balance > summary.current_balance


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_assets_list():
    result = project_portfolio([], months=12)
    assert result.current_total == Decimal("0.00")
    for m in result.monthly:
        assert m.portfolio_total == Decimal("0.00")


def test_custom_start_date():
    a = _asset(balance="10000", rate="0.0")
    start = date(2025, 1, 31)
    result = project_portfolio([a], months=1, start_date=start)
    # 1 month from Jan 31 → Feb 28 (non-leap year)
    assert result.monthly[0].date == date(2025, 2, 28)
