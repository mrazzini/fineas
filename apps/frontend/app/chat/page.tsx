import { ChatPanel } from "@/components/chat/ChatPanel";
import Link from "next/link";

export default function ChatPage() {
  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <header className="border-b bg-white px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Fineas</h1>
          <p className="text-xs text-muted-foreground">Your FIRE copilot</p>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            Dashboard
          </Link>
          <span className="font-medium">Chat</span>
          <Link href="/projections" className="text-muted-foreground hover:text-foreground">
            Projections
          </Link>
        </nav>
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="mx-auto max-w-2xl h-full">
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
