"""
Integration tests for POST /ingest and POST /assets/{id}/snapshots/upsert.

LLM mock strategy:
  We patch `agent.nodes.get_llm` to return a MagicMock whose call chain
  mirrors what nodes.py expects:

      get_llm()
        .with_structured_output(ParsedPortfolioUpdate)
        .ainvoke([...])         ← returns a preset ParsedPortfolioUpdate

  This keeps tests fast (~milliseconds) and deterministic — no API key needed.

DB:
  The standard `client` fixture from conftest.py is used; it spins up a real
  test database with all tables created.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from agent.llm_schemas import ParsedAsset, ParsedPortfolioUpdate, ParsedSnapshot


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_llm_mock(parsed: ParsedPortfolioUpdate) -> MagicMock:
    """
    Build a mock that behaves like get_llm() for the parse node.

    Chain: get_llm() → .with_structured_output() → .ainvoke() → parsed
    """
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=parsed)
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


def _etf_response() -> ParsedPortfolioUpdate:
    return ParsedPortfolioUpdate(
        assets=[ParsedAsset(name="Vanguard ETF", asset_type="STOCKS", ticker="VWCE.DE")],
        snapshots=[ParsedSnapshot(asset_name="Vanguard ETF", snapshot_date="2026-02-01", balance=12578.0)],
    )


# ── POST /ingest ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_happy_path(client):
    mock_llm = _make_llm_mock(_etf_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest", json={"text": "My Vanguard ETF is worth €12,578 as of Feb 2026"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_valid"] is True
    assert body["validation_errors"] == []
    assert len(body["validated_assets"]) == 1
    assert body["validated_assets"][0]["asset_type"] == "STOCKS"
    assert len(body["validated_snapshots"]) == 1
    assert body["validated_snapshots"][0]["balance"] == 12578.0


@pytest.mark.asyncio
async def test_ingest_exposes_raw_and_validated(client):
    """Response always includes both raw LLM output and validated items."""
    mock_llm = _make_llm_mock(_etf_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest", json={"text": "anything"})

    body = resp.json()
    assert "parsed_assets" in body
    assert "validated_assets" in body
    # For valid input they should be equal (modulo type normalisation)
    assert len(body["parsed_assets"]) == len(body["validated_assets"])


@pytest.mark.asyncio
async def test_ingest_validation_errors_set_is_valid_false(client):
    """When the LLM returns an unknown asset_type, is_valid must be False."""
    bad_response = ParsedPortfolioUpdate(
        assets=[ParsedAsset(name="Mystery", asset_type="spaceship")],
        snapshots=[],
    )
    mock_llm = _make_llm_mock(bad_response)
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest", json={"text": "some text"})

    body = resp.json()
    assert body["is_valid"] is False
    assert len(body["validation_errors"]) > 0
    assert body["validated_assets"] == []


@pytest.mark.asyncio
async def test_ingest_empty_text_returns_empty_lists(client):
    """Empty or whitespace text should result in empty lists, no errors."""
    empty_response = ParsedPortfolioUpdate(assets=[], snapshots=[])
    mock_llm = _make_llm_mock(empty_response)
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest", json={"text": ""})

    body = resp.json()
    assert body["is_valid"] is True
    assert body["validated_assets"] == []
    assert body["validated_snapshots"] == []
    assert body["validation_errors"] == []


@pytest.mark.asyncio
async def test_ingest_response_includes_ambiguous_assets_key(client):
    """Response always includes ambiguous_assets (may be empty for clean inputs)."""
    mock_llm = _make_llm_mock(_etf_response())
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest", json={"text": "My Vanguard ETF is worth 12k"})

    body = resp.json()
    assert "ambiguous_assets" in body
    assert isinstance(body["ambiguous_assets"], list)
    # Clean, unambiguous input → no disambiguation needed
    assert body["ambiguous_assets"] == []


@pytest.mark.asyncio
async def test_ingest_multiple_assets_and_snapshots(client):
    """Multiple assets and snapshots in one request all pass through."""
    multi = ParsedPortfolioUpdate(
        assets=[
            ParsedAsset(name="ETF", asset_type="STOCKS"),
            ParsedAsset(name="Cash", asset_type="CASH"),
        ],
        snapshots=[
            ParsedSnapshot(asset_name="ETF",  snapshot_date="2026-02-01", balance=12000.0),
            ParsedSnapshot(asset_name="Cash", snapshot_date="2026-02-01", balance=5000.0),
        ],
    )
    mock_llm = _make_llm_mock(multi)
    with patch("agent.nodes.get_llm", return_value=mock_llm):
        resp = await client.post("/ingest", json={"text": "ETF 12k, Cash 5k"})

    body = resp.json()
    assert body["is_valid"] is True
    assert len(body["validated_assets"]) == 2
    assert len(body["validated_snapshots"]) == 2


# ── POST /assets/{id}/snapshots/upsert ─────────────────────────────────────

@pytest_asyncio.fixture
async def asset_id(client):
    """Create a throwaway asset and return its ID."""
    resp = await client.post("/assets", json={
        "name": "Upsert Test Asset",
        "asset_type": "CASH",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_upsert_creates_snapshot(client, asset_id):
    resp = await client.post(
        f"/assets/{asset_id}/snapshots/upsert",
        json={"snapshot_date": "2026-01-01", "balance": "1000.00"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"] == asset_id
    assert Decimal(body["balance"]) == Decimal("1000.00")


@pytest.mark.asyncio
async def test_upsert_updates_existing_snapshot(client, asset_id):
    """Calling upsert twice with the same date updates the balance."""
    date = "2026-02-01"
    await client.post(
        f"/assets/{asset_id}/snapshots/upsert",
        json={"snapshot_date": date, "balance": "1000.00"},
    )
    resp = await client.post(
        f"/assets/{asset_id}/snapshots/upsert",
        json={"snapshot_date": date, "balance": "2500.00"},
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["balance"]) == Decimal("2500.00")

    # Confirm only one row exists for this date.
    list_resp = await client.get(f"/assets/{asset_id}/snapshots")
    snapshots_on_date = [s for s in list_resp.json() if s["snapshot_date"] == date]
    assert len(snapshots_on_date) == 1


@pytest.mark.asyncio
async def test_upsert_unknown_asset_returns_404(client):
    import uuid
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/assets/{fake_id}/snapshots/upsert",
        json={"snapshot_date": "2026-01-01", "balance": "500.00"},
    )
    assert resp.status_code == 404
