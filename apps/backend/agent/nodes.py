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

    return {
        "validated_assets": validated_assets,
        "validated_snapshots": validated_snapshots,
        "validation_errors": errors,
    }
