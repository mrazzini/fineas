"""
LangGraph node functions for the ingestion graph.

A node is just a plain async function with the signature:
    async def node_name(state: IngestState) -> dict

It receives the full current state and returns a *partial* dict containing
only the keys it changed.  LangGraph merges the returned dict into the state.

Four nodes:
  [parse]        — calls the LLM, returns parsed_assets + parsed_snapshots
  [validate]     — pure Python checks, returns validated_* + validation_errors
  [human_review] — Phase 4: interrupt() suspends graph; resumes with human decision
  [apply]        — Phase 4: writes validated data to the database
"""
import uuid
from datetime import date as date_type
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_llm
from agent.llm_schemas import ParsedPortfolioUpdate
from agent.prompts import PARSE_SYSTEM_PROMPT
from agent.state import IngestState

# Valid asset_type values (lower-cased for case-insensitive matching).
# Maps common aliases → canonical enum value.
_ASSET_TYPE_MAP: dict[str, str] = {
    "cash": "CASH",
    "stocks": "STOCKS",
    "stock": "STOCKS",
    "equity": "STOCKS",
    "equities": "STOCKS",
    "etf": "STOCKS",
    "shares": "STOCKS",
    "bonds": "BONDS",
    "bond": "BONDS",
    "real_estate": "REAL_ESTATE",
    "realestate": "REAL_ESTATE",
    "property": "REAL_ESTATE",
    "crypto": "CRYPTO",
    "cryptocurrency": "CRYPTO",
    "bitcoin": "CRYPTO",
    "pension_fund": "PENSION_FUND",
    "pension": "PENSION_FUND",
    "retirement": "PENSION_FUND",
    "other": "OTHER",
}
_VALID_ASSET_TYPES = {"CASH", "STOCKS", "BONDS", "REAL_ESTATE", "CRYPTO", "PENSION_FUND", "OTHER"}


async def parse(state: IngestState) -> dict:
    """
    [Node 1 — LLM] Extract structured asset/snapshot data from raw text.

    Uses `.with_structured_output()` so the LLM returns a typed
    ParsedPortfolioUpdate object instead of plain text.  No JSON parsing
    needed — LangChain handles the tool-calling protocol under the hood.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(ParsedPortfolioUpdate)

    result: ParsedPortfolioUpdate = await structured_llm.ainvoke([
        SystemMessage(content=PARSE_SYSTEM_PROMPT),
        HumanMessage(content=state["raw_text"]),
    ])

    return {
        "parsed_assets": [a.model_dump() for a in result.assets],
        "parsed_snapshots": [s.model_dump() for s in result.snapshots],
    }


def _normalise_asset_type(raw: str) -> str | None:
    """Map a raw string to a canonical AssetType enum value, or return None."""
    # Try exact match first (handles already-correct values like "STOCKS").
    if raw in _VALID_ASSET_TYPES:
        return raw
    return _ASSET_TYPE_MAP.get(raw.lower().replace(" ", "_"))


async def validate(state: IngestState) -> dict:
    """
    [Node 2 — Pure Python] Validate the LLM's output against business rules.

    No LLM call here — this is deterministic logic.  It:
      1. Normalises asset_type strings to canonical enum values.
      2. Checks snapshot_date strings parse as valid ISO dates.
      3. Checks balances are non-negative.
      4. Detects duplicate (asset_name, snapshot_date) pairs in the same request.

    Phase 4: if human_corrections are present in state (set by human_review after
    a "correct" decision), those override parsed_assets / parsed_snapshots before
    validation runs.  Corrections are cleared from state after processing.

    Items that pass all checks → validated_*
    Items with any problem   → validation_errors (human-readable strings)
    """
    corrections = state.get("human_corrections") or {}
    assets = corrections.get("assets") if corrections.get("assets") is not None else state.get("parsed_assets", [])
    snapshots = corrections.get("snapshots") if corrections.get("snapshots") is not None else state.get("parsed_snapshots", [])

    validated_assets: list[dict] = []
    validated_snapshots: list[dict] = []
    errors: list[str] = []

    # ── Validate assets ────────────────────────────────────────────────────
    for asset in assets:
        canonical_type = _normalise_asset_type(asset.get("asset_type", ""))
        if canonical_type is None:
            errors.append(
                f"Asset '{asset.get('name', '?')}': unknown asset_type "
                f"'{asset.get('asset_type')}'. "
                f"Valid values: {', '.join(sorted(_VALID_ASSET_TYPES))}."
            )
            continue
        validated_assets.append({**asset, "asset_type": canonical_type})

    # ── Validate snapshots ─────────────────────────────────────────────────
    seen: set[tuple[str, str]] = set()

    for snap in snapshots:
        name = snap.get("asset_name", "?")
        date_str = snap.get("snapshot_date", "")
        balance = snap.get("balance")
        item_ok = True

        # Date format check
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            errors.append(
                f"Snapshot for '{name}': invalid snapshot_date '{date_str}'. "
                "Expected YYYY-MM-DD."
            )
            item_ok = False

        # Balance check
        if balance is None or balance < 0:
            errors.append(
                f"Snapshot for '{name}' on {date_str}: "
                f"balance must be a non-negative number, got '{balance}'."
            )
            item_ok = False

        # Duplicate check
        key = (name, date_str)
        if key in seen:
            errors.append(
                f"Snapshot for '{name}' on {date_str} appears more than once "
                "in this request."
            )
            item_ok = False
        else:
            seen.add(key)

        if item_ok:
            validated_snapshots.append(snap)

    result: dict = {
        "validated_assets": validated_assets,
        "validated_snapshots": validated_snapshots,
        "validation_errors": errors,
    }

    # If corrections were applied, update parsed data to reflect what was actually
    # validated, and clear corrections so they don't re-apply on next loop.
    if corrections.get("assets") is not None:
        result["parsed_assets"] = assets
    if corrections.get("snapshots") is not None:
        result["parsed_snapshots"] = snapshots
    if corrections:
        result["human_corrections"] = {}

    return result


async def human_review(state: IngestState) -> dict:
    """
    [Node 3 — HITL] Suspend the graph and wait for human input.

    Calls interrupt() which pauses execution here and returns the payload to
    whoever called ainvoke().  The graph's state is checkpointed so it can
    resume later.

    When resumed via ainvoke(Command(resume={...})), the value passed to
    Command(resume=...) becomes the return value of interrupt() here.

    Decision routing (handled by _route_after_human_review in graph.py):
      "approve"  → skip re-validation, apply validated items that already passed
      "correct"  → merge corrections into state, re-run validate
      "reject"   → route to END, no DB writes
    """
    from langgraph.types import interrupt  # local import to keep mock surface small

    decision = interrupt({
        "validation_errors": state["validation_errors"],
        "parsed_assets": state["parsed_assets"],
        "parsed_snapshots": state["parsed_snapshots"],
    })

    return {
        "human_decision": decision.get("action", "reject"),
        "human_corrections": decision.get("corrections") or {},
    }


async def apply(state: IngestState) -> dict:
    """
    [Node 4 — DB Write] Persist validated assets and snapshots to the database.

    Assets are upserted by name (SELECT-then-INSERT to handle the UNIQUE
    constraint cleanly).  Snapshots are upserted via PostgreSQL's
    ON CONFLICT ... DO UPDATE using the existing uq_snapshot_asset_date
    constraint.

    Uses AsyncSessionLocal directly — not via FastAPI DI — because this node
    runs inside LangGraph, not inside a request context.  Tests can mock
    agent.nodes.AsyncSessionLocal to avoid real DB writes.
    """
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from database import AsyncSessionLocal
    from models import Asset, AssetSnapshot

    assets_to_apply = state.get("validated_assets", [])
    snapshots_to_apply = state.get("validated_snapshots", [])

    asset_name_to_id: dict[str, uuid.UUID] = {}
    applied_assets = 0
    applied_snapshots = 0

    async with AsyncSessionLocal() as db:
        # ── Upsert assets ──────────────────────────────────────────────────
        for asset_data in assets_to_apply:
            result = await db.execute(
                select(Asset).where(Asset.name == asset_data["name"])
            )
            asset = result.scalar_one_or_none()

            if asset is None:
                asset = Asset(
                    name=asset_data["name"],
                    asset_type=asset_data["asset_type"],
                    ticker=asset_data.get("ticker"),
                    annualized_return_pct=asset_data.get("annualized_return_pct"),
                )
                db.add(asset)
                await db.flush()  # assign the UUID without committing yet
            else:
                # Overwrite mutable fields; never overwrite is_archived.
                asset.asset_type = asset_data["asset_type"]
                if asset_data.get("ticker") is not None:
                    asset.ticker = asset_data["ticker"]
                if asset_data.get("annualized_return_pct") is not None:
                    asset.annualized_return_pct = asset_data["annualized_return_pct"]

            asset_name_to_id[asset.name] = asset.id
            applied_assets += 1

        # ── Upsert snapshots ───────────────────────────────────────────────
        for snap_data in snapshots_to_apply:
            asset_name = snap_data["asset_name"]
            asset_id = asset_name_to_id.get(asset_name)

            if asset_id is None:
                # Asset wasn't in validated_assets — look it up in DB.
                result = await db.execute(
                    select(Asset).where(Asset.name == asset_name)
                )
                existing = result.scalar_one_or_none()
                if existing is None:
                    continue  # no matching asset; skip snapshot
                asset_id = existing.id
                asset_name_to_id[asset_name] = asset_id

            snapshot_date = date_type.fromisoformat(snap_data["snapshot_date"])
            stmt = (
                pg_insert(AssetSnapshot)
                .values(
                    asset_id=asset_id,
                    snapshot_date=snapshot_date,
                    balance=snap_data["balance"],
                )
                .on_conflict_do_update(
                    constraint="uq_snapshot_asset_date",
                    set_={"balance": snap_data["balance"]},
                )
            )
            await db.execute(stmt)
            applied_snapshots += 1

        await db.commit()

    return {
        "applied_assets_count": applied_assets,
        "applied_snapshots_count": applied_snapshots,
    }
