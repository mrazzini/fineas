"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentResponse, AssetUpdate } from "@/types/schema";
import { createChatSocket } from "../websocket";

export interface ChatEntry {
  id: string;
  role: "user" | "agent";
  content: string;
  isThinking?: boolean;
  confirmationData?: AssetUpdate[];
}

export function useChat() {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [waitingConfirmation, setWaitingConfirmation] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = createChatSocket();
    socketRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as AgentResponse;

      if (msg.type === "thinking") {
        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: "agent", content: msg.content, isThinking: true },
        ]);
      } else if (msg.type === "response" || msg.type === "update_complete") {
        setMessages((prev) => {
          // Replace last thinking bubble or append
          const withoutThinking = prev.filter((m) => !m.isThinking);
          return [
            ...withoutThinking,
            { id: crypto.randomUUID(), role: "agent", content: msg.content },
          ];
        });
      } else if (msg.type === "confirmation_request") {
        setWaitingConfirmation(true);
        setMessages((prev) => {
          const withoutThinking = prev.filter((m) => !m.isThinking);
          return [
            ...withoutThinking,
            {
              id: crypto.randomUUID(),
              role: "agent",
              content: msg.content,
              confirmationData: msg.data?.updates,
            },
          ];
        });
      } else if (msg.type === "error") {
        setMessages((prev) => [
          ...prev.filter((m) => !m.isThinking),
          { id: crypto.randomUUID(), role: "agent", content: `Error: ${msg.content}` },
        ]);
      }
    };

    return () => ws.close();
  }, []);

  const sendMessage = useCallback((content: string) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content },
    ]);
    socketRef.current.send(JSON.stringify({ type: "user_message", content }));
  }, []);

  const confirm = useCallback((confirmed: boolean, edits?: Record<string, number>) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    setWaitingConfirmation(false);
    socketRef.current.send(JSON.stringify({ type: "confirmation_response", confirmed, edits }));
  }, []);

  return { messages, connected, waitingConfirmation, sendMessage, confirm };
}
