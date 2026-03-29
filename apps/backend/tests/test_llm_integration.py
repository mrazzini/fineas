"""
Real LLM integration tests for the smart import pipeline.

Unlike the rest of the test suite, these tests do NOT mock the LLM.  They
make actual API calls to verify the model's extraction quality end-to-end.

Run selectively to avoid unnecessary token spend:
    pytest -m llm -v

All tests are skipped automatically when no API key is present, so the
standard CI suite (which has no key) continues to pass.

Root-cause note
---------------
"I want to reset my stocks to 12000" returns is_valid=True with empty lists:
- The LLM returns assets=[], snapshots=[] because "reset" implies deletion
  and "stocks" is a category, not a named asset.
- is_valid = len(validation_errors) == 0 → True (no errors on empty lists).
- The UI button is disabled={!is_valid || !hasSelection}; with nothing to
  select hasSelection=False → button disabled.
test_llm_reset_stocks_produces_no_data below documents this behaviour.
"""
import os
from datetime import date

import pytest

from agent import build_apply_graph, ingest_graph

# ---------------------------------------------------------------------------
# Skip the entire module when no LLM provider key is available
# ---------------------------------------------------------------------------
_HAS_KEY = bool(
    os.getenv("ANTHROPIC_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("GROQ_API_KEY")
)

pytestmark = pytest.mark.skipif(
    not _HAS_KEY,
    reason="No LLM API key configured — set ANTHROPIC_API_KEY (or OPENROUTER_API_KEY / GROQ_API_KEY) to run",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _initial_state(text: str) -> dict:
    return {
        "raw_text": text,
        "parsed_assets": [],
        "parsed_snapshots": [],
        "validated_assets": [],
        "validated_snapshots": [],
        "validation_errors": [],
    }


# ---------------------------------------------------------------------------
# Test 1 — Happy path: clear, unambiguous ETF description
# ---------------------------------------------------------------------------

@pytest.mark.llm
async def test_llm_clear_etf_extracts_correctly():
    """
    A fully-specified ETF description should be extracted without errors.

    Checks:
    - Exactly one STOCKS asset with the correct ticker.
    - Exactly one snapshot with the correct balance and date.
    - No validation errors.
    """
    state = await ingest_graph.ainvoke(
        _initial_state(
            "My Vanguard FTSE All-World ETF (VWCE.DE) is worth €12,578 as of February 2026"
        )
    )

    assert state["validation_errors"] == [], state["validation_errors"]

    assets = state["validated_assets"]
    assert len(assets) == 1
    assert assets[0]["asset_type"] == "STOCKS"
    assert assets[0].get("ticker") == "VWCE.DE"

    snaps = state["validated_snapshots"]
    assert len(snaps) == 1
    assert snaps[0]["balance"] == 12578.0
    assert snaps[0]["snapshot_date"] == "2026-02-01"


# ---------------------------------------------------------------------------
# Test 2 — Bug reproduction: "reset my stocks to 12000"
# ---------------------------------------------------------------------------

@pytest.mark.llm
async def test_llm_reset_stocks_produces_no_data():
    """
    "reset my stocks to 12000" triggers the reported UI bug.

    The phrase contains no named asset and "reset" implies a deletion
    operation that is outside the extraction schema.  The model should
    return empty lists rather than invent an asset name.

    Result: is_valid=True (no errors) but validated_assets=[] and
    validated_snapshots=[] → hasSelection=False → UI button disabled.
    """
    state = await ingest_graph.ainvoke(
        _initial_state("I want to reset my stocks to 12000")
    )

    # No validation errors — empty input is valid.
    assert state["validation_errors"] == [], state["validation_errors"]

    # Nothing extracted — this is the root cause of the disabled button.
    assert state["validated_assets"] == [], (
        "Expected no assets: 'stocks' is a category, not a named asset. "
        f"Got: {state['validated_assets']}"
    )
    assert state["validated_snapshots"] == [], (
        "Expected no snapshots: without a named asset the snapshot is unanchored. "
        f"Got: {state['validated_snapshots']}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Date inference: no date in input
# ---------------------------------------------------------------------------

@pytest.mark.llm
async def test_llm_no_explicit_date_infers_today():
    """
    When no date is mentioned the LLM should fall back to today's date.

    Checks:
    - One CASH asset extracted.
    - One snapshot with balance 5000 and a valid ISO date.
    """
    state = await ingest_graph.ainvoke(
        _initial_state("My savings account has €5,000")
    )

    assert state["validation_errors"] == [], state["validation_errors"]

    snaps = state["validated_snapshots"]
    assert len(snaps) == 1, f"Expected 1 snapshot, got {snaps}"
    assert snaps[0]["balance"] == 5000.0

    snap_date = snaps[0]["snapshot_date"]
    # Must be a valid ISO date string.
    parsed = date.fromisoformat(snap_date)  # raises ValueError if malformed
    assert parsed is not None


# ---------------------------------------------------------------------------
# Test 4 — Multi-asset portfolio
# ---------------------------------------------------------------------------

@pytest.mark.llm
async def test_llm_multi_asset_portfolio():
    """
    A portfolio with two distinct asset types and explicit balances/dates
    should yield exactly two assets and two snapshots, each correctly typed.
    """
    text = (
        "As of March 2026 my Vanguard FTSE ETF is worth €20,000 "
        "and my pension fund sits at €45,500."
    )

    state = await ingest_graph.ainvoke(_initial_state(text))

    assert state["validation_errors"] == [], state["validation_errors"]

    assets = state["validated_assets"]
    assert len(assets) == 2, f"Expected 2 assets, got {assets}"

    types = {a["asset_type"] for a in assets}
    assert "STOCKS" in types, f"Expected a STOCKS asset, got types: {types}"
    assert "PENSION_FUND" in types, f"Expected a PENSION_FUND asset, got types: {types}"

    snaps = state["validated_snapshots"]
    assert len(snaps) == 2, f"Expected 2 snapshots, got {snaps}"

    balances = {s["balance"] for s in snaps}
    assert 20000.0 in balances
    assert 45500.0 in balances


# ---------------------------------------------------------------------------
# Test 5 — Full HITL flow via HTTP (real LLM + DB write)
# ---------------------------------------------------------------------------

@pytest.mark.llm
async def test_llm_full_hitl_end_to_end(client):
    """
    End-to-end: POST /ingest (real LLM) → POST /ingest/apply → GET /assets.

    Exercises the complete HITL path including the HTTP layer and DB writes.
    """
    # Step 1: parse
    parse_resp = await client.post(
        "/ingest",
        json={"text": "My iShares Core MSCI World ETF (IWDA.AS) is worth €8,750 as of January 2026"},
    )
    assert parse_resp.status_code == 200
    parse_body = parse_resp.json()

    assert parse_body["is_valid"] is True, parse_body.get("validation_errors")
    assert len(parse_body["validated_assets"]) >= 1
    assert len(parse_body["validated_snapshots"]) >= 1

    # Step 2: apply (human approved — pass through)
    apply_resp = await client.post(
        "/ingest/apply",
        json={
            "validated_assets": parse_body["validated_assets"],
            "validated_snapshots": parse_body["validated_snapshots"],
        },
    )
    assert apply_resp.status_code == 200
    apply_body = apply_resp.json()
    assert apply_body["success"] is True, apply_body.get("apply_errors")
    assert len(apply_body["applied_assets"]) >= 1
    assert len(apply_body["applied_snapshots"]) >= 1

    # Step 3: verify the asset is persisted in the DB
    assets_resp = await client.get("/assets")
    assert assets_resp.status_code == 200
    names = [a["name"] for a in assets_resp.json()]
    applied_name = apply_body["applied_assets"][0]["name"]
    assert applied_name in names, f"'{applied_name}' not found in DB assets: {names}"
