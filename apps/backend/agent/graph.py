"""
Ingestion graph — wires nodes together and compiles to a runnable.

Graph topology:

    START → [parse_with_context] → [validate] → END

The parse node is stateless — existing-asset context arrives via state,
not from a DB read — so the graph compiles once at import time.

The apply graph is still built per-request because each invocation needs
its own AsyncSession.
"""
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from agent.nodes import make_apply_node, parse, parse_with_context, validate
from agent.state import IngestState


def _build_parse_validate(parse_node) -> CompiledStateGraph:
    builder = StateGraph(IngestState)
    builder.add_node("parse", parse_node)
    builder.add_node("validate", validate)
    builder.add_edge(START, "parse")
    builder.add_edge("parse", "validate")
    builder.add_edge("validate", END)
    return builder.compile()


# Stateless singletons — no DB, safe to reuse across requests.
ingest_graph = _build_parse_validate(parse)
ingest_graph_with_context = _build_parse_validate(parse_with_context)


def build_apply_graph(db: AsyncSession) -> CompiledStateGraph:
    """One-node graph that writes validated data to the DB.

    Per-request: each invocation binds a fresh AsyncSession.
    """
    builder = StateGraph(IngestState)
    builder.add_node("apply", make_apply_node(db))
    builder.add_edge(START, "apply")
    builder.add_edge("apply", END)
    return builder.compile()


def build_pipeline_graph(db: AsyncSession) -> CompiledStateGraph:
    """Full pipeline: parse → validate → apply. Non-interactive flows."""
    builder = StateGraph(IngestState)
    builder.add_node("parse", parse_with_context)
    builder.add_node("validate", validate)
    builder.add_node("apply", make_apply_node(db))
    builder.add_edge(START, "parse")
    builder.add_edge("parse", "validate")
    builder.add_edge("validate", "apply")
    builder.add_edge("apply", END)
    return builder.compile()
