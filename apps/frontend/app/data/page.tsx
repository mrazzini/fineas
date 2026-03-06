import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataManager } from "@/components/data/DataManager";
import { getAssets } from "@/lib/api";
import Link from "next/link";

export default async function DataPage() {
  let assets = [];
  try {
    assets = await getAssets({ includeInactive: true });
  } catch {
    // API not available
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Fineas</h1>
          <p className="text-xs text-muted-foreground">Your FIRE copilot</p>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            Dashboard
          </Link>
          <Link href="/chat" className="text-muted-foreground hover:text-foreground">
            Chat
          </Link>
          <Link href="/projections" className="text-muted-foreground hover:text-foreground">
            Projections
          </Link>
          <span className="font-medium">Data</span>
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Manage Data</h2>
          <p className="text-sm text-muted-foreground mt-1">
            View, add, edit, and delete snapshots per asset.
          </p>
        </div>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Snapshots</CardTitle>
          </CardHeader>
          <CardContent>
            {assets.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                API not reachable — start the backend first.
              </p>
            ) : (
              <DataManager assets={assets} />
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
