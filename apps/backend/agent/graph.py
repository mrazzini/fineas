"""
Ingestion graph — wires nodes together and compiles to a runnable.

LangGraph concepts used here:
  StateGraph   — the container; you add nodes and edges to it
  START / END  — sentinel nodes marking entry and exit points
  add_node()   — registers a function as a named node
  add_edge()   — draws a directed arrow between two nodes
  compile()    — validates the graph and returns a CompiledGraph you can invoke

The compiled graph is a module-level singleton.  FastAPI imports `ingest_graph`
once at startup; there is no per-request compilation overhead.

Graph topology (Phase 3):

    START
      │
      ▼
    [parse]      ← LLM call: raw text → parsed_assets + parsed_snapshots
      │
      ▼
    [validate]   ← Pure Python: normalise + check → validated_* + errors
      │
      ▼
    END

In Phase 4 this will grow: a conditional edge after [validate] will route to
a human-approval node when is_valid is False, and to an [apply] node when True.
"""
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from agent.nodes import make_apply_node, make_parse_node, parse, validate
from agent.state import IngestState

# ── Build ──────────────────────────────────────────────────────────────────
_builder = StateGraph(IngestState)

_builder.add_node("parse", parse)
_builder.add_node("validate", validate)

_builder.add_edge(START, "parse")
_builder.add_edge("parse", "validate")
_builder.add_edge("validate", END)

# ── Compile ────────────────────────────────────────────────────────────────
# compile() validates that every node is reachable and that there are no
# dead ends, then returns a CompiledGraph with .invoke() / .ainvoke() methods.
ingest_graph = _builder.compile()


# ── Phase 4: Apply graph (per-request, needs a DB session) ────────────────

def build_context_ingest_graph(db: AsyncSession) -> CompiledStateGraph:
    """
    Parse+validate graph where the parse node fetches the user's existing
    portfolio from the DB and injects it into the LLM prompt.

    Used by the production POST /ingest endpoint.  Per-request (not a
    singleton) because each request needs its own DB session.
    """
    builder = StateGraph(IngestState)
    builder.add_node("parse", make_parse_node(db))
    builder.add_node("validate", validate)
    builder.add_edge(START, "parse")
    builder.add_edge("parse", "validate")
    builder.add_edge("validate", END)
    return builder.compile()


def build_apply_graph(db: AsyncSession) -> CompiledStateGraph:
    """
    Build a one-node graph that writes validated data to the database.

    Not a singleton — each invocation needs its own DB session so we build
    a fresh graph per request.
    """
    apply_node = make_apply_node(db)
    builder = StateGraph(IngestState)
    builder.add_node("apply", apply_node)
    builder.add_edge(START, "apply")
    builder.add_edge("apply", END)
    return builder.compile()


def build_pipeline_graph(db: AsyncSession) -> CompiledStateGraph:
    """
    Full pipeline: parse -> validate -> apply.

    Useful for non-interactive flows where no HITL review is needed.
    """
    apply_node = make_apply_node(db)
    builder = StateGraph(IngestState)
    builder.add_node("parse", parse)
    builder.add_node("validate", validate)
    builder.add_node("apply", apply_node)
    builder.add_edge(START, "parse")
    builder.add_edge("parse", "validate")
    builder.add_edge("validate", "apply")
    builder.add_edge("apply", END)
    return builder.compile()
