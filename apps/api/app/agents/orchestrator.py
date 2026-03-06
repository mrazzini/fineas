"""
Agent Orchestrator — Phase 1.

Single LLM call classifies user intent, then routes to the appropriate agent.
Manages per-conversation graph config for the WebSocket lifecycle.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi import WebSocket
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.update_agent import UpdateAgentState, build_update_graph
from app.config import settings
from app.database import AsyncSessionLocal

log = logging.getLogger(__name__)

# Per-conversation LangGraph config (thread_id → config dict)
# Graphs are rebuilt per-call with a fresh session but share _CHECKPOINTER
_active_configs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

CLASSIFY_PROMPT = """You are Fineas, a FIRE portfolio copilot router.
Classify the user's message into one of these intents:
- "update": User wants to update asset values (monthly update)
- "projection": User asks about FIRE projections or timeline
- "goal": User wants to set or modify a financial goal
- "monitor": User asks about portfolio drift or alerts
- "general": General question, greeting, or unclear intent

Return JSON only: {"intent": "<intent>", "confidence": 0.0}
"""


async def _classify_intent(message: str) -> str:
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=64,
    )
    response = await llm.ainvoke([
        SystemMessage(content=CLASSIFY_PROMPT),
        HumanMessage(content=message),
    ])
    try:
        raw = response.content.strip().strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        return data.get("intent", "general")
    except Exception:
        return "general"


# ---------------------------------------------------------------------------
# WebSocket handlers
# ---------------------------------------------------------------------------

async def handle_message(
    websocket: WebSocket,
    message: str,
    conversation_id: str,
) -> None:
    """Route an incoming user message to the appropriate agent."""
    await websocket.send_json({"type": "thinking", "content": "Thinking…"})

    async with AsyncSessionLocal() as session:
        intent = await _classify_intent(message)
        log.info("conversation=%s intent=%s", conversation_id, intent)

        if intent == "update":
            await _run_update_agent(websocket, message, conversation_id, session)
        else:
            await _general_response(websocket, message, intent, session)


async def _run_update_agent(
    websocket: WebSocket,
    message: str,
    conversation_id: str,
    session: AsyncSession,
) -> None:
    """Start an Update Agent run and pause at the confirmation interrupt."""
    graph = build_update_graph(session)

    config = {"configurable": {"thread_id": conversation_id}}
    _active_configs[conversation_id] = config

    initial_state = UpdateAgentState(
        messages=[{"role": "user", "content": message}],
        parsed_updates=[],
        current_holdings={},
        deltas=[],
        anomalies=[],
        user_confirmed=False,
        write_results=[],
        snapshot_date=date.today().isoformat(),
        error=None,
    )

    # Consume all events until the graph pauses (interrupt_before) or finishes
    async for event in graph.astream(initial_state, config, stream_mode="values"):
        pass

    # After the stream ends, check if the graph is paused at an interrupt
    state = await graph.aget_state(config)

    if state.next:
        # Graph is paused — present the confirmation request
        v = state.values
        msgs = v.get("messages", [])
        last_assistant = next(
            (m["content"] for m in reversed(msgs) if m["role"] == "assistant"),
            "Please review the proposed changes below.",
        )
        await websocket.send_json({
            "type": "confirmation_request",
            "content": last_assistant,
            "data": {
                "updates": v.get("deltas", []),
                "anomalies": v.get("anomalies", []),
                "snapshot_date": v.get("snapshot_date"),
            },
        })
    else:
        # Graph completed normally (no updates found, error, etc.)
        v = state.values if state else {}
        error = v.get("error")
        msgs = v.get("messages", [])
        if error:
            await websocket.send_json({"type": "error", "content": error})
        else:
            last_assistant = next(
                (m["content"] for m in reversed(msgs) if m["role"] == "assistant"), None
            )
            if last_assistant:
                await websocket.send_json({"type": "response", "content": last_assistant})
            else:
                await websocket.send_json({
                    "type": "response",
                    "content": "I couldn't find any asset updates in your message. Please try again.",
                })


async def handle_confirmation(
    websocket: WebSocket,
    conversation_id: str,
    confirmed: bool,
    edits: dict[str, float] | None = None,
) -> None:
    """Resume the paused Update Agent with the user's confirmation decision."""
    config = _active_configs.get(conversation_id)

    if not config:
        await websocket.send_json({
            "type": "error",
            "content": "No active update session. Please start a new message.",
        })
        return

    await websocket.send_json({"type": "thinking", "content": "Saving updates…"})

    async with AsyncSessionLocal() as session:
        # Rebuild graph with fresh session — _CHECKPOINTER is module-level so
        # checkpoint state from the first run is preserved.
        graph = build_update_graph(session)

        # Inject user's decision into the checkpoint state
        await graph.aupdate_state(
            config,
            {"user_confirmed": confirmed},
            as_node="write_updates",
        )

        # Resume execution from the interrupted point
        async for event in graph.astream(None, config, stream_mode="values"):
            pass

        final_state = await graph.aget_state(config)
        if final_state and final_state.values:
            v = final_state.values
            msgs = v.get("messages", [])
            last_assistant = next(
                (m["content"] for m in reversed(msgs) if m["role"] == "assistant"), None
            )
            if last_assistant:
                msg_type = "update_complete" if confirmed else "response"
                await websocket.send_json({"type": msg_type, "content": last_assistant})

    # Cleanup conversation state
    _active_configs.pop(conversation_id, None)


async def _general_response(
    websocket: WebSocket, message: str, intent: str, session: AsyncSession
) -> None:
    """Handle non-update intents with a portfolio-aware LLM response."""
    from app.tools.portfolio import make_portfolio_tools

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=512,
    )

    # Fetch live portfolio data so the LLM can answer factual questions
    try:
        tools = make_portfolio_tools(session)
        summary = await tools["get_net_worth_summary"]()
        portfolio_lines = [
            f"- {h['asset_name']}: €{h['current_amount']:,.0f}"
            for h in summary["holdings"]
        ]
        portfolio_context = (
            f"Current portfolio (total €{summary['total_net_worth']:,.0f}):\n"
            + "\n".join(portfolio_lines)
        )
    except Exception:
        portfolio_context = "Portfolio data unavailable."

    system = (
        "You are Fineas, a friendly FIRE portfolio copilot. "
        "You help users track investments and plan for financial independence. "
        f"{portfolio_context}\n\n"
        f"The user's intent was classified as '{intent}'. "
        "Use the portfolio data above to answer questions accurately. "
        "If it's a projection or goal question, briefly explain that full projection tools are coming in Phase 2. "
        "Keep responses concise and helpful."
    )

    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=message),
    ])

    await websocket.send_json({"type": "response", "content": response.content})
