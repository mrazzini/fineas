"use client";

import type { ChatEntry } from "@/lib/hooks/useChat";

interface Props {
  entry: ChatEntry;
}

export function MessageBubble({ entry }: Props) {
  const isUser = entry.role === "user";

  if (entry.isThinking) {
    return (
      <div className="flex items-start gap-3">
        <div className="h-7 w-7 rounded-full bg-emerald-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
          F
        </div>
        <div className="rounded-2xl bg-white border border-slate-100 px-4 py-2.5 shadow-sm">
          <span className="flex gap-1 items-center h-5">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" />
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
          isUser ? "bg-slate-700 text-white" : "bg-emerald-600 text-white"
        }`}
      >
        {isUser ? "M" : "F"}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
          isUser
            ? "bg-slate-800 text-white rounded-tr-sm"
            : "bg-white border border-slate-100 text-slate-800 shadow-sm rounded-tl-sm"
        }`}
      >
        {entry.content}
      </div>
    </div>
  );
}
