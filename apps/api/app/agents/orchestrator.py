"""
Agent Orchestrator — Phase 1.

Single LLM call classifies user intent, then routes to the appropriate agent.
Manages per-conversation graph state for the WebSocket lifecycle.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi import WebSocket
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.update_agent import UpdateAgentState, build_update_graph
from app.config import settings
from app.database import AsyncSessionLocal

log = logging.getLogger(__name__)

# In-memory store of active graphs per conversation_id
# In production this would use Redis/PostgreSQL-backed checkpointer
_active_graphs: dict[str, Any] = {}
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
            # General response for Phase 1 (other agents in Phase 2+)
            await _general_response(websocket, message, intent)


async def _run_update_agent(
    websocket: WebSocket,
    message: str,
    conversation_id: str,
    session: AsyncSession,
) -> None:
    """Start or continue an Update Agent run."""
    graph = build_update_graph(session)
    _active_graphs[conversation_id] = graph

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

    # Stream events until interrupt or END
    async for event in graph.astream(initial_state, config, stream_mode="values"):
        # Check if we hit the confirmation interrupt
        if "__interrupt__" in event or event.get("deltas") and not event.get("user_confirmed"):
            deltas = event.get("deltas", [])
            anomalies = event.get("anomalies", [])

            if deltas:
                # Find the last assistant message
                msgs = event.get("messages", [])
                confirmation_text = msgs[-1]["content"] if msgs else "Please review the changes below."

                await websocket.send_json({
                    "type": "confirmation_request",
                    "content": confirmation_text,
                    "data": {
                        "updates": deltas,
                        "anomalies": anomalies,
                        "snapshot_date": event.get("snapshot_date"),
                    },
                })
                return  # Pause — wait for confirmation_response

    # If we reach here with no interrupt, check for error or completion
    # This handles the case where parse found nothing
    final_state = await graph.aget_state(config)
    if final_state and final_state.values:
        v = final_state.values
        error = v.get("error")
        msgs = v.get("messages", [])
        if error:
            await websocket.send_json({"type": "error", "content": error})
        elif msgs:
            last_assistant = next(
                (m["content"] for m in reversed(msgs) if m["role"] == "assistant"), None
            )
            if last_assistant:
                await websocket.send_json({"type": "response", "content": last_assistant})


async def handle_confirmation(
    websocket: WebSocket,
    conversation_id: str,
    confirmed: bool,
    edits: dict[str, float] | None = None,
) -> None:
    """Resume the paused Update Agent with the user's confirmation decision."""
    graph = _active_graphs.get(conversation_id)
    config = _active_configs.get(conversation_id)

    if not graph or not config:
        await websocket.send_json({
            "type": "error",
            "content": "No active update session. Please start a new message.",
        })
        return

    # Apply any edits to the interrupt value
    resume_value = {"confirmed": confirmed, "edits": edits or {}}

    await websocket.send_json({"type": "thinking", "content": "Saving updates…"})

    async with AsyncSessionLocal() as session:
        # Re-build graph with fresh session for the write phase
        graph = build_update_graph(session)
        _active_graphs[conversation_id] = graph

        # Resume from interrupt
        async for event in graph.astream(
            {"user_confirmed": confirmed},
            config,
            stream_mode="values",
        ):
            pass  # consume events

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

    # Cleanup
    _active_graphs.pop(conversation_id, None)
    _active_configs.pop(conversation_id, None)


async def _general_response(websocket: WebSocket, message: str, intent: str) -> None:
    """Handle non-update intents with a simple LLM response."""
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=512,
    )

    system = (
        "You are Fineas, a friendly FIRE portfolio copilot. "
        "You help users track investments and plan for financial independence. "
        f"The user's intent was classified as '{intent}'. "
        "If it's a projection or goal question, briefly explain that full projection tools are coming in Phase 2. "
        "Keep responses concise and helpful."
    )

    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=message),
    ])

    await websocket.send_json({"type": "response", "content": response.content})
