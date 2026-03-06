function resolveWSBase(): string {
  const { protocol, hostname } = window.location;
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    const http = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return http.replace(/^http/, "ws");
  }
  // Codespaces / remote: replace frontend port suffix with API port
  const apiHostname = hostname.replace(/-3001\./, "-8000.");
  return `${wsProtocol}//${apiHostname}`;
}

export function createChatSocket(): WebSocket {
  return new WebSocket(`${resolveWSBase()}/api/chat/`);
}
