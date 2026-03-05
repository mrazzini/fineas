"""Chat WebSocket router — Phase 1 NL Update Agent integration."""
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/")
async def chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    conversation_id = str(uuid.uuid4())

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "user_message":
                # Import here to avoid circular imports and allow lazy loading
                from app.agents.orchestrator import handle_message

                await handle_message(websocket, data["content"], conversation_id)

            elif msg_type == "confirmation_response":
                from app.agents.orchestrator import handle_confirmation

                await handle_confirmation(
                    websocket,
                    conversation_id,
                    confirmed=data.get("confirmed", False),
                    edits=data.get("edits"),
                )
            else:
                await websocket.send_json(
                    {"type": "error", "content": f"Unknown message type: {msg_type}"}
                )
    except WebSocketDisconnect:
        pass
