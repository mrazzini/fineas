"use client";

import { useEffect, useRef, useState } from "react";
import { ConfirmationCard } from "@/components/chat/ConfirmationCard";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { useChat } from "@/lib/hooks/useChat";

export function ChatPanel() {
  const { messages, connected, waitingConfirmation, sendMessage, confirm } = useChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || waitingConfirmation) return;
    sendMessage(text);
    setInput("");
  };

  // Find the last confirmation message
  const confirmationEntry = [...messages].reverse().find((m) => m.confirmationData);

  return (
    <div className="flex flex-col h-full">
      {/* Connection status */}
      <div className="px-4 py-2 border-b bg-white flex items-center gap-2 text-xs text-muted-foreground">
        <span
          className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-slate-300"}`}
        />
        {connected ? "Connected to Fineas" : "Connecting…"}
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 bg-slate-50">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-sm pt-16 space-y-1">
            <p className="text-2xl">👋</p>
            <p className="font-medium text-slate-700">Hi, I'm Fineas</p>
            <p>Tell me your monthly update — I'll do the rest.</p>
            <p className="text-xs mt-4 italic text-slate-400">
              e.g. "March update: stocks 13,500, Xtrackers 4,800, everything else same"
            </p>
          </div>
        )}

        {messages.map((entry) => (
          <div key={entry.id}>
            {entry.confirmationData ? (
              <div className="space-y-2">
                <MessageBubble entry={{ ...entry, confirmationData: undefined }} />
                {confirmationEntry?.id === entry.id && waitingConfirmation && (
                  <ConfirmationCard
                    updates={entry.confirmationData}
                    onConfirm={(edits) => confirm(true, edits)}
                    onCancel={() => confirm(false)}
                  />
                )}
              </div>
            ) : (
              <MessageBubble entry={entry} />
            )}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="border-t bg-white px-4 py-3 flex gap-2 items-end"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e as unknown as React.FormEvent);
            }
          }}
          placeholder={
            waitingConfirmation
              ? "Waiting for your confirmation above…"
              : "Tell Fineas your update…"
          }
          disabled={waitingConfirmation}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-50 disabled:text-slate-400 leading-relaxed"
        />
        <button
          type="submit"
          disabled={!input.trim() || waitingConfirmation || !connected}
          className="h-10 w-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center disabled:opacity-40 hover:bg-emerald-700 transition-colors shrink-0"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>
    </div>
  );
}
