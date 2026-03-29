"""
Unit tests for the [validate] node.

These tests exercise only pure Python logic — no LLM call, no database.
They run in milliseconds and need no environment variables.

The [parse] node is tested separately in test_ingest.py with a mocked LLM.

Why test nodes in isolation?
  Nodes are plain async functions: (state) → partial_state_dict.
  Calling them directly is trivial and gives fast, deterministic feedback.
  This is one of LangGraph's advantages over monolithic LLM chains.
"""
import pytest

from agent.nodes import validate


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_state(assets=None, snapshots=None):
    """Build a minimal IngestState for the validate node."""
    return {
        "raw_text": "",
        "parsed_assets": assets or [],
        "parsed_snapshots": snapshots or [],
        "validated_assets": [],
        "validated_snapshots": [],
        "validation_errors": [],
    }


# ── Asset validation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_valid_asset():
    state = _make_state(assets=[{"name": "Vanguard ETF", "asset_type": "STOCKS"}])
    result = await validate(state)
    assert result["validated_assets"] == [{"name": "Vanguard ETF", "asset_type": "STOCKS"}]
    assert result["validation_errors"] == []


@pytest.mark.asyncio
async def test_validate_case_insensitive_asset_type():
    """'stocks' (lowercase) should normalise to 'STOCKS'."""
    state = _make_state(assets=[{"name": "My ETF", "asset_type": "stocks"}])
    result = await validate(state)
    assert result["validated_assets"][0]["asset_type"] == "STOCKS"
    assert result["validation_errors"] == []


@pytest.mark.asyncio
async def test_validate_alias_asset_type():
    """Common aliases should be accepted and normalised."""
    aliases = [
        ("equity", "STOCKS"),
        ("etf", "STOCKS"),
        ("shares", "STOCKS"),
        ("pension", "PENSION_FUND"),
        ("retirement", "PENSION_FUND"),
        ("property", "REAL_ESTATE"),
        ("bitcoin", "CRYPTO"),
    ]
    for raw, expected in aliases:
        state = _make_state(assets=[{"name": "A", "asset_type": raw}])
        result = await validate(state)
        assert result["validated_assets"][0]["asset_type"] == expected, f"Failed for alias '{raw}'"
        assert result["validation_errors"] == []


@pytest.mark.asyncio
async def test_validate_unknown_asset_type():
    """An unrecognised asset_type goes to errors, not validated_assets."""
    state = _make_state(assets=[{"name": "Foo", "asset_type": "spaceship"}])
    result = await validate(state)
    assert result["validated_assets"] == []
    assert len(result["validation_errors"]) == 1
    assert "spaceship" in result["validation_errors"][0]


# ── Snapshot validation ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_valid_snapshot():
    state = _make_state(snapshots=[{
        "asset_name": "Cash", "snapshot_date": "2026-02-01", "balance": 5000.0
    }])
    result = await validate(state)
    assert len(result["validated_snapshots"]) == 1
    assert result["validation_errors"] == []


@pytest.mark.asyncio
async def test_validate_bad_date():
    """A non-ISO date string should produce a validation error."""
    state = _make_state(snapshots=[{
        "asset_name": "Cash", "snapshot_date": "Feb 2026", "balance": 5000.0
    }])
    result = await validate(state)
    assert result["validated_snapshots"] == []
    assert any("snapshot_date" in e for e in result["validation_errors"])


@pytest.mark.asyncio
async def test_validate_negative_balance():
    state = _make_state(snapshots=[{
        "asset_name": "Cash", "snapshot_date": "2026-02-01", "balance": -100.0
    }])
    result = await validate(state)
    assert result["validated_snapshots"] == []
    assert any("non-negative" in e for e in result["validation_errors"])


@pytest.mark.asyncio
async def test_validate_zero_balance_is_ok():
    """Zero is a valid balance (e.g. an account that was closed)."""
    state = _make_state(snapshots=[{
        "asset_name": "Cash", "snapshot_date": "2026-02-01", "balance": 0.0
    }])
    result = await validate(state)
    assert len(result["validated_snapshots"]) == 1
    assert result["validation_errors"] == []


@pytest.mark.asyncio
async def test_validate_duplicate_snapshot():
    """Two snapshots for the same (asset_name, date) should produce an error."""
    snap = {"asset_name": "ETF", "snapshot_date": "2026-01-01", "balance": 1000.0}
    state = _make_state(snapshots=[snap, snap])
    result = await validate(state)
    # Only the first occurrence passes; the second is an error.
    assert len(result["validated_snapshots"]) == 1
    assert any("more than once" in e for e in result["validation_errors"])


@pytest.mark.asyncio
async def test_validate_mixed_valid_and_invalid():
    """Valid items should pass through even when others fail."""
    state = _make_state(
        assets=[
            {"name": "Good", "asset_type": "CASH"},
            {"name": "Bad", "asset_type": "moonrock"},
        ],
        snapshots=[
            {"asset_name": "Good", "snapshot_date": "2026-01-01", "balance": 500.0},
            {"asset_name": "Good", "snapshot_date": "bad-date", "balance": 500.0},
        ],
    )
    result = await validate(state)
    assert len(result["validated_assets"]) == 1
    assert result["validated_assets"][0]["name"] == "Good"
    assert len(result["validated_snapshots"]) == 1
    assert len(result["validation_errors"]) == 2


@pytest.mark.asyncio
async def test_validate_empty_input():
    """Empty state should produce empty outputs with no errors."""
    state = _make_state()
    result = await validate(state)
    assert result["validated_assets"] == []
    assert result["validated_snapshots"] == []
    assert result["validation_errors"] == []


# ── Disambiguation detection ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_extracts_ambiguous_assets():
    """Assets with match_candidates are surfaced in ambiguous_assets."""
    state = _make_state(assets=[{
        "name": "ETF",
        "asset_type": "STOCKS",
        "match_candidates": ["Global Equity ETF", "Vanguard ETF"],
    }])
    result = await validate(state)
    assert len(result["ambiguous_assets"]) == 1
    amb = result["ambiguous_assets"][0]
    assert amb["original_name"] == "ETF"
    assert "Global Equity ETF" in amb["candidates"]
    assert "Vanguard ETF" in amb["candidates"]
    # match_candidates must be stripped from validated_assets
    assert "match_candidates" not in result["validated_assets"][0]
    # The asset still appears in validated_assets using the LLM's best-guess name
    assert result["validated_assets"][0]["name"] == "ETF"


@pytest.mark.asyncio
async def test_validate_non_ambiguous_asset_produces_empty_ambiguous():
    """Normal assets (no match_candidates) produce empty ambiguous_assets."""
    state = _make_state(assets=[{"name": "My ETF", "asset_type": "STOCKS"}])
    result = await validate(state)
    assert result["ambiguous_assets"] == []
    assert result["validated_assets"] == [{"name": "My ETF", "asset_type": "STOCKS"}]
