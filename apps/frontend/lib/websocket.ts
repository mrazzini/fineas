const WS_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") ?? "ws://localhost:8000";

export function createChatSocket(): WebSocket {
  return new WebSocket(`${WS_BASE}/api/chat/`);
}
