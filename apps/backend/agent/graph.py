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

from agent.nodes import parse, validate
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
