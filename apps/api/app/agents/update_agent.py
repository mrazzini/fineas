"""
NL Update Agent — Phase 1.

Flow: parse_input → fetch_current → compute_deltas → present_confirmation
      → [INTERRUPT before write_updates] → write_updates → respond → END

Human-in-the-loop is enforced at the graph level: interrupt_before=["write_updates"].
No DB writes can happen without user confirmation, regardless of LLM behavior.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from app.config import settings
from app.tools.portfolio import AssetDelta, make_portfolio_tools

log = logging.getLogger(__name__)

# Module-level shared checkpointer — survives across graph rebuilds so that
# checkpoint state persists from initial run through the confirmation resume.
_CHECKPOINTER = MemorySaver()


# ---------------------------------------------------------------------------
# Agent State
# ---------------------------------------------------------------------------

class ParsedUpdate(TypedDict):
    asset_name: str
    new_amount: float | None          # absolute value (preferred)
    delta: float | None               # relative change (e.g. "add 1000")


class UpdateAgentState(TypedDict):
    messages: list[dict]  # {role, content}
    parsed_updates: list[ParsedUpdate]
    current_holdings: dict[str, dict]  # name → HoldingInfo dict
    deltas: list[dict]  # AssetDelta dicts
    anomalies: list[str]
    user_confirmed: bool
    write_results: list[dict]
    snapshot_date: str  # ISO date
    error: str | None


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Fineas, a FIRE portfolio copilot.
Your job is to extract asset value updates from natural language messages.

The user tracks these assets:
- Pure Cash Liquidity (cash, isyBank)
- Long-Term Stocks (stocks, Scalable Capital)
- iBonds (bonds, Scalable Capital)
- Xtrackers EUR Overnight (money market, Scalable Capital)
- Lyxor SMART (money market, Scalable Capital)
- Esketit (P2P lending)
- Estateguru (P2P lending)
- Fonchim (pension fund)

When the user says "everything else same", do NOT include those assets — they will be carried forward unchanged.

Return a JSON array. Always include both "new_amount" and "delta" keys; set the unused one to null.
- Use "new_amount" for absolute values: "set lyxor smart to 5000" → new_amount=5000.00, delta=null
- Use "delta" for relative changes: "add 1000 to lyxor smart" or "increase by 500" → new_amount=null, delta=1000.00
- For reductions: "remove 200 from stocks" → new_amount=null, delta=-200.00

Example:
[
  {"asset_name": "Long-Term Stocks", "new_amount": 13500.00, "delta": null},
  {"asset_name": "Lyxor SMART", "new_amount": null, "delta": 1000.00}
]

Return ONLY the JSON array, no other text. If you cannot extract any updates, return [].
"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=1024,
    )


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

async def parse_input(state: UpdateAgentState) -> dict:
    """Extract structured updates from the user's natural language message."""
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    log.info("parse_input: %s", last_msg[:100])

    llm = _llm()
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=last_msg),
    ])

    raw = response.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        raw = raw.rstrip("`").strip()

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            parsed = []
    except json.JSONDecodeError:
        log.warning("parse_input: could not decode JSON: %s", raw)
        parsed = []

    return {"parsed_updates": parsed}


async def fetch_current(state: UpdateAgentState, session: AsyncSession) -> dict:
    """Get latest snapshot per active asset."""
    tools = make_portfolio_tools(session)
    holdings = await tools["get_current_holdings"]()
    log.info("fetch_current: %d holdings", len(holdings))
    return {"current_holdings": holdings}


async def compute_deltas(state: UpdateAgentState, session: AsyncSession) -> dict:
    """Match parsed updates to current holdings and compute deltas."""
    tools = make_portfolio_tools(session)

    deltas = []
    anomalies = []

    for upd in state["parsed_updates"]:
        match_result = await tools["get_asset_by_name"](upd["asset_name"])

        if match_result.get("error") or not match_result.get("asset_name"):
            anomalies.append(f"Could not match '{upd['asset_name']}': {match_result.get('error', 'unknown')}")
            continue

        matched_name = match_result["asset_name"]
        holding = state["current_holdings"].get(matched_name)

        if not holding:
            anomalies.append(f"No current snapshot found for '{matched_name}'")
            continue

        new_amount = upd.get("new_amount")
        relative_delta = upd.get("delta")

        if new_amount is None and relative_delta is not None:
            new_amount = holding["current_amount"] + relative_delta
        elif new_amount is None:
            anomalies.append(f"Could not determine new value for '{upd['asset_name']}'")
            continue

        delta = AssetDelta(
            asset_name=matched_name,
            asset_id=holding["asset_id"],
            old_amount=holding["current_amount"],
            new_amount=new_amount,
        )
        deltas.append(delta.to_dict())

        if delta.is_anomaly:
            anomalies.append(
                f"⚠ {matched_name}: {delta.anomaly_reason} "
                f"(€{delta.old_amount:,.0f} → €{delta.new_amount:,.0f})"
            )

    # Portfolio-level anomaly check
    old_total = sum(h["current_amount"] for h in state["current_holdings"].values())
    updated_holdings = dict(state["current_holdings"])
    for d in deltas:
        if d["asset_name"] in updated_holdings:
            updated_holdings[d["asset_name"]] = {**updated_holdings[d["asset_name"]], "current_amount": d["new_amount"]}
    new_total = sum(h["current_amount"] for h in updated_holdings.values())

    if old_total > 0:
        portfolio_change_pct = abs((new_total - old_total) / old_total * 100)
        if portfolio_change_pct > 15:
            anomalies.append(
                f"⚠ Portfolio total change {portfolio_change_pct:.1f}% exceeds 15% threshold "
                f"(€{old_total:,.0f} → €{new_total:,.0f})"
            )

    return {"deltas": deltas, "anomalies": anomalies}


async def present_confirmation(state: UpdateAgentState) -> dict:
    """Format the confirmation summary for the user."""
    if not state["deltas"]:
        return {
            "error": "No valid updates found. Please rephrase and try again.",
        }

    lines = ["Here's what I'll update:\n"]
    for d in state["deltas"]:
        sign = "+" if d["delta"] >= 0 else ""
        lines.append(
            f"  • {d['asset_name']}: €{d['old_amount']:,.0f} → €{d['new_amount']:,.0f} "
            f"({sign}{d['delta_pct']:.1f}%)"
        )

    if state["anomalies"]:
        lines.append("\n**Warnings:**")
        for w in state["anomalies"]:
            lines.append(f"  {w}")

    lines.append(f"\nSnapshot date: {state['snapshot_date']}")
    lines.append("\nPlease confirm, edit, or cancel.")

    return {"messages": state["messages"] + [{"role": "assistant", "content": "\n".join(lines)}]}


async def write_updates(state: UpdateAgentState, session: AsyncSession) -> dict:
    """Write confirmed snapshots to the database."""
    if not state.get("user_confirmed"):
        return {"write_results": [], "messages": state["messages"] + [
            {"role": "assistant", "content": "Update cancelled. No changes were made."}
        ]}

    tools = make_portfolio_tools(session)

    updates_payload = [
        {
            "asset_id": d["asset_id"],
            "asset_name": d["asset_name"],
            "date": state["snapshot_date"],
            "amount": d["new_amount"],
        }
        for d in state["deltas"]
    ]

    results = await tools["batch_update_snapshots"](updates_payload)
    log.info("write_updates: %d results", len(results))
    return {"write_results": results}


async def respond(state: UpdateAgentState, session: AsyncSession) -> dict:
    """Final confirmation message with updated net worth."""
    if not state.get("user_confirmed"):
        return {}  # already handled in write_updates

    tools = make_portfolio_tools(session)
    summary = await tools["get_net_worth_summary"]()

    successes = [r for r in state.get("write_results", []) if r.get("success")]
    failures = [r for r in state.get("write_results", []) if not r.get("success")]

    lines = [f"✓ Updated {len(successes)} asset(s) successfully."]
    if failures:
        lines.append(f"⚠ {len(failures)} update(s) failed: {', '.join(r['asset_name'] for r in failures)}")
    lines.append(f"\nNew total net worth: €{summary['total_net_worth']:,.0f}")

    return {
        "messages": state["messages"] + [{"role": "assistant", "content": "\n".join(lines)}]
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_after_parse(state: UpdateAgentState) -> Literal["fetch_current", END]:
    if state.get("error"):
        return END
    return "fetch_current"


def route_after_confirmation(state: UpdateAgentState) -> Literal["write_updates", END]:
    if not state["deltas"] or state.get("error"):
        return END
    return "write_updates"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_update_graph(session: AsyncSession) -> Any:
    """Build and compile the update agent graph with session injection.

    Uses the module-level _CHECKPOINTER so state persists across graph
    rebuilds (e.g. when a fresh session is needed for the write phase).
    """

    # Partial-apply session into nodes that need DB access
    async def _fetch_current(state):
        return await fetch_current(state, session)

    async def _compute_deltas(state):
        return await compute_deltas(state, session)

    async def _write_updates(state):
        return await write_updates(state, session)

    async def _respond(state):
        return await respond(state, session)

    builder = StateGraph(UpdateAgentState)

    builder.add_node("parse_input", parse_input)
    builder.add_node("fetch_current", _fetch_current)
    builder.add_node("compute_deltas", _compute_deltas)
    builder.add_node("present_confirmation", present_confirmation)
    builder.add_node("write_updates", _write_updates)
    builder.add_node("respond", _respond)

    builder.set_entry_point("parse_input")
    builder.add_conditional_edges("parse_input", route_after_parse)
    builder.add_edge("fetch_current", "compute_deltas")
    builder.add_edge("compute_deltas", "present_confirmation")
    builder.add_conditional_edges("present_confirmation", route_after_confirmation)
    builder.add_edge("write_updates", "respond")
    builder.add_edge("respond", END)

    graph = builder.compile(
        checkpointer=_CHECKPOINTER,      # shared singleton — survives rebuilds
        interrupt_before=["write_updates"],
    )
    return graph
