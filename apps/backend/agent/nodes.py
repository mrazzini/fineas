"""
LangGraph node functions for the ingestion graph.

A node is just a plain async function with the signature:
    async def node_name(state: IngestState) -> dict

It receives the full current state and returns a *partial* dict containing
only the keys it changed.  LangGraph merges the returned dict into the state.

Two nodes:
  [parse]    — calls the LLM, returns parsed_assets + parsed_snapshots
  [validate] — pure Python checks, returns validated_* + validation_errors
"""
from datetime import date, datetime
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm import get_llm
from agent.llm_schemas import ParsedPortfolioUpdate
from agent.prompts import PARSE_SYSTEM_PROMPT, ExistingAsset, build_parse_prompt
from agent.state import IngestState
from models import Asset, AssetSnapshot, AssetType

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


async def _fetch_existing_assets(db: AsyncSession) -> list[ExistingAsset]:
    """
    Return all non-archived assets with their most recent balance in one query.

    Uses ROW_NUMBER() over (PARTITION BY asset_id ORDER BY snapshot_date DESC)
    to get the latest snapshot per asset without N+1 queries.
    Assets with no snapshots get latest_balance=None.
    """
    ranked = (
        select(
            AssetSnapshot.asset_id,
            AssetSnapshot.balance,
            func.row_number()
                .over(
                    partition_by=AssetSnapshot.asset_id,
                    order_by=AssetSnapshot.snapshot_date.desc(),
                )
                .label("rn"),
        )
        .subquery()
    )
    stmt = (
        select(
            Asset.name,
            Asset.asset_type,
            Asset.ticker,
            ranked.c.balance.label("latest_balance"),
        )
        .where(Asset.is_archived == False)  # noqa: E712
        .outerjoin(ranked, (Asset.id == ranked.c.asset_id) & (ranked.c.rn == 1))
        .order_by(Asset.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        ExistingAsset(
            name=row.name,
            asset_type=str(
                row.asset_type.value
                if hasattr(row.asset_type, "value")
                else row.asset_type
            ),
            ticker=row.ticker,
            latest_balance=float(row.latest_balance) if row.latest_balance is not None else None,
        )
        for row in rows
    ]


def make_parse_node(db: AsyncSession) -> Callable:
    """
    Factory: returns a parse node that fetches existing portfolio assets from
    the DB and injects them into the LLM prompt before extraction.

    Used by `build_context_ingest_graph` in the production endpoint.
    The bare `parse` function above is kept for the static `ingest_graph`
    singleton (used by all mocked tests) — zero regressions.
    """

    async def parse_with_context(state: IngestState) -> dict:
        existing_assets = await _fetch_existing_assets(db)
        prompt = build_parse_prompt(existing_assets)

        llm = get_llm()
        structured_llm = llm.with_structured_output(ParsedPortfolioUpdate)
        result: ParsedPortfolioUpdate = await structured_llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=state["raw_text"]),
        ])
        return {
            "parsed_assets": [a.model_dump() for a in result.assets],
            "parsed_snapshots": [s.model_dump() for s in result.snapshots],
        }

    return parse_with_context


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

    Items that pass all checks → validated_*
    Items with any problem   → validation_errors (human-readable strings)
    """
    validated_assets: list[dict] = []
    validated_snapshots: list[dict] = []
    errors: list[str] = []

    # ── Validate assets ────────────────────────────────────────────────────
    for asset in state.get("parsed_assets", []):
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

    for snap in state.get("parsed_snapshots", []):
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

    # ── Detect ambiguous assets ────────────────────────────────────────────
    # Assets where the LLM returned match_candidates need user disambiguation.
    # Surface them separately and strip the field from validated_assets so it
    # doesn't leak into the HTTP response or confuse the apply node.
    ambiguous: list[dict] = []
    for i, asset in enumerate(validated_assets):
        candidates = asset.get("match_candidates")
        if candidates:
            ambiguous.append({
                "asset_index": i,
                "original_name": asset["name"],
                "candidates": candidates,
            })
    validated_assets = [
        {k: v for k, v in a.items() if k != "match_candidates"}
        for a in validated_assets
    ]

    return {
        "validated_assets": validated_assets,
        "validated_snapshots": validated_snapshots,
        "validation_errors": errors,
        "ambiguous_assets": ambiguous,
    }


def make_apply_node(db: AsyncSession) -> Callable:
    """
    Factory: returns an async node function that writes validated data to the DB.

    Takes an AsyncSession so each invocation gets its own transaction context.
    The node does find-or-create for assets and upsert for snapshots in a single
    commit, accumulating per-item errors in apply_errors.
    """

    async def apply(state: IngestState) -> dict:
        applied_assets: list[dict] = []
        applied_snapshots: list[dict] = []
        apply_errors: list[str] = []
        name_to_id: dict[str, str] = {}

        # ── Find-or-create assets ───────────────────────────────────────
        for asset_data in state.get("validated_assets", []):
            name = asset_data.get("name", "")
            # Apply any user-supplied disambiguation: "ETF" → "Global Equity ETF"
            name = state.get("resolved_names", {}).get(name, name)
            try:
                # Check if asset already exists
                result = await db.execute(
                    select(Asset).where(Asset.name == name)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    name_to_id[name.lower()] = str(existing.id)
                    applied_assets.append({
                        "name": existing.name,
                        "asset_id": str(existing.id),
                        "status": "matched",
                    })
                else:
                    # Resolve asset_type enum
                    raw_type = asset_data.get("asset_type", "OTHER")
                    try:
                        asset_type = AssetType(raw_type)
                    except ValueError:
                        apply_errors.append(
                            f"Asset '{name}': invalid asset_type '{raw_type}'."
                        )
                        continue

                    new_asset = Asset(
                        name=name,
                        asset_type=asset_type,
                        ticker=asset_data.get("ticker"),
                        annualized_return_pct=asset_data.get("annualized_return_pct"),
                    )
                    db.add(new_asset)
                    await db.flush()  # get the generated id
                    name_to_id[name.lower()] = str(new_asset.id)
                    applied_assets.append({
                        "name": new_asset.name,
                        "asset_id": str(new_asset.id),
                        "status": "created",
                    })
            except Exception as exc:
                apply_errors.append(f"Asset '{name}': {exc}")

        # ── Upsert snapshots ────────────────────────────────────────────
        for snap_data in state.get("validated_snapshots", []):
            asset_name = snap_data.get("asset_name", "")
            # Resolve the snapshot's asset_name using the same disambiguation map
            resolved_asset_name = state.get("resolved_names", {}).get(asset_name, asset_name)
            asset_id = name_to_id.get(resolved_asset_name.lower())

            if not asset_id:
                apply_errors.append(
                    f"Snapshot for '{asset_name}': no matching asset found."
                )
                continue

            try:
                # Convert string date to date object for asyncpg
                snap_date = snap_data["snapshot_date"]
                if isinstance(snap_date, str):
                    snap_date = date.fromisoformat(snap_date)

                stmt = pg_insert(AssetSnapshot).values(
                    asset_id=asset_id,
                    snapshot_date=snap_date,
                    balance=snap_data["balance"],
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_snapshot_asset_date",
                    set_={"balance": stmt.excluded.balance},
                )
                await db.execute(stmt)
                applied_snapshots.append({
                    "asset_name": asset_name,
                    "asset_id": asset_id,
                    "snapshot_date": snap_data["snapshot_date"],
                    "balance": snap_data["balance"],
                    "status": "upserted",
                })
            except Exception as exc:
                apply_errors.append(
                    f"Snapshot for '{asset_name}' on "
                    f"{snap_data.get('snapshot_date', '?')}: {exc}"
                )

        await db.commit()

        return {
            "applied_assets": applied_assets,
            "applied_snapshots": applied_snapshots,
            "apply_errors": apply_errors,
        }

    return apply
