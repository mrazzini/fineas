"""
Ingestion graph — wires nodes together and compiles to a runnable.

LangGraph concepts used here:
  StateGraph        — the container; you add nodes and edges to it
  START / END       — sentinel nodes marking entry and exit points
  add_node()        — registers a function as a named node
  add_edge()        — draws a directed arrow between two nodes
  add_conditional_edges() — routes to different nodes based on state
  compile()         — validates the graph and returns a CompiledGraph
  MemorySaver       — in-memory checkpointer; persists state between invocations
                      so interrupt() / Command(resume=...) work across requests

The compiled graph is a module-level singleton.  FastAPI imports `ingest_graph`
once at startup; there is no per-request compilation overhead.

Graph topology (Phase 4 — with HITL):

    START
      │
      ▼
    [parse]        ← LLM: raw text → parsed_assets + parsed_snapshots
      │
      ▼
    [validate]     ← Pure Python: normalise + check → validated_* + errors
      │
      ▼ (conditional)
      ├─ is_valid ──────────────────────────────→ [apply] → END
      │
      └─ has errors → [human_review]
                           │  ← interrupt() pauses here
                           │
                           ▼ (conditional on human_decision)
                           ├─ "reject"  → END
                           ├─ "approve" → [apply] → END
                           └─ "correct" → [validate] → ... (loop)
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import apply, human_review, parse, validate
from agent.state import IngestState

# ── Parse-only graph (Phase 3 legacy — no HITL, no DB writes) ─────────────
# Used by POST /ingest for backwards-compatible parse-and-validate behaviour.
# No checkpointer needed — each call is stateless.
_parse_builder = StateGraph(IngestState)
_parse_builder.add_node("parse", parse)
_parse_builder.add_node("validate", validate)
_parse_builder.add_edge(START, "parse")
_parse_builder.add_edge("parse", "validate")
_parse_builder.add_edge("validate", END)
parse_graph = _parse_builder.compile()


# ── Routing functions ───────────────────────────────────────────────────────

def _route_after_validate(state: IngestState) -> str:
    """Route to human_review when validation found problems, otherwise apply."""
    if state.get("validation_errors"):
        return "human_review"
    return "apply"


def _route_after_human_review(state: IngestState) -> str:
    """
    Route based on the human's decision:
      approve → apply the items that already passed validation (skip re-validation)
      correct → re-validate with the human's corrections
      reject  → end without writing anything
    """
    decision = state.get("human_decision", "reject")
    if decision == "approve":
        return "apply"
    if decision == "correct":
        return "validate"
    return END  # "reject" or unknown


# ── Build ──────────────────────────────────────────────────────────────────
_builder = StateGraph(IngestState)

_builder.add_node("parse", parse)
_builder.add_node("validate", validate)
_builder.add_node("human_review", human_review)
_builder.add_node("apply", apply)

_builder.add_edge(START, "parse")
_builder.add_edge("parse", "validate")
_builder.add_conditional_edges("validate", _route_after_validate)
_builder.add_conditional_edges("human_review", _route_after_human_review)
_builder.add_edge("apply", END)

# ── Compile ────────────────────────────────────────────────────────────────
# MemorySaver persists graph state in-process so that interrupted runs can be
# resumed by a subsequent ainvoke(Command(resume=...)) call with the same
# thread_id.  For production, swap MemorySaver for a PostgreSQL-backed
# checkpointer (langgraph-checkpoint-postgres) to survive process restarts.
_checkpointer = MemorySaver()

ingest_graph = _builder.compile(checkpointer=_checkpointer)
