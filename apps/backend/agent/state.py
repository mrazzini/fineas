"""
IngestState — the shared "sticky note" that flows through every node in the
ingestion graph.

LangGraph passes this TypedDict between nodes.  Each node receives the
*current* state and returns a *partial* dict with only the keys it changed.
LangGraph merges that partial dict back into the full state automatically.

Why TypedDict and not a dataclass or Pydantic model?
  LangGraph requires a plain dict-like type so it can do efficient merging.
  TypedDict gives us static-typing hints without the overhead of Pydantic
  validation on every state transition.
"""
from typing import TypedDict


class IngestState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────
    raw_text: str             # the user's free-form text or pasted CSV

    # ── After the [parse] node ─────────────────────────────────────────────
    parsed_assets: list[dict]     # raw LLM-extracted asset definitions
    parsed_snapshots: list[dict]  # raw LLM-extracted balance snapshots

    # ── After the [validate] node ──────────────────────────────────────────
    validated_assets: list[dict]     # items that passed all validation rules
    validated_snapshots: list[dict]  # items that passed all validation rules
    validation_errors: list[str]     # human-readable descriptions of any problems

    # ── After the [apply] node (Phase 4) ─────────────────────────────────
    applied_assets: list[dict]       # assets created or matched in DB
    applied_snapshots: list[dict]    # snapshots upserted in DB
    apply_errors: list[str]          # per-item failures during apply
