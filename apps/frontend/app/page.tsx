import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AllocationBreakdown } from "@/components/dashboard/AllocationBreakdown";
import { NetWorthChart } from "@/components/dashboard/NetWorthChart";
import { ProjectionCurve } from "@/components/dashboard/ProjectionCurve";
import { SnapshotTable } from "@/components/dashboard/SnapshotTable";
import { getNetWorthHistory, getPortfolioSummary } from "@/lib/api";
import Link from "next/link";

export default async function DashboardPage() {
  let summary = null;
  let history = null;

  try {
    [summary, history] = await Promise.all([getPortfolioSummary(), getNetWorthHistory()]);
  } catch {
    // API not available — show offline banner
  }

  const formatEUR = (v: number) =>
    new Intl.NumberFormat("it-IT", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 0,
    }).format(v);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b bg-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Fineas</h1>
          <p className="text-xs text-muted-foreground">Your FIRE copilot</p>
        </div>
        <nav className="flex gap-4 text-sm">
          <span className="font-medium">Dashboard</span>
          <Link href="/chat" className="text-muted-foreground hover:text-foreground">
            Chat
          </Link>
          <Link href="/projections" className="text-muted-foreground hover:text-foreground">
            Projections
          </Link>
          <Link href="/data" className="text-muted-foreground hover:text-foreground">
            Data
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8 space-y-6">
        {/* Net worth hero */}
        <div>
          <p className="text-sm text-muted-foreground">Total Net Worth</p>
          <p className="text-4xl font-bold tabular-nums">
            {summary ? formatEUR(summary.total_net_worth) : "—"}
          </p>
          {summary && (
            <p className="text-xs text-muted-foreground mt-1">
              as of{" "}
              {new Date(summary.as_of_date).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          )}
        </div>

        {/* API offline banner */}
        {!summary && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            API not reachable — start the backend with{" "}
            <code className="font-mono text-xs bg-amber-100 px-1 rounded">
              docker compose up api
            </code>{" "}
            or{" "}
            <code className="font-mono text-xs bg-amber-100 px-1 rounded">
              cd apps/api && uvicorn app.main:app --reload
            </code>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Net worth chart */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">Net Worth History</CardTitle>
            </CardHeader>
            <CardContent>
              <NetWorthChart data={history ?? []} />
            </CardContent>
          </Card>

          {/* Allocation donut */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              {summary ? (
                <AllocationBreakdown
                  holdings={summary.holdings}
                  total={summary.total_net_worth}
                />
              ) : (
                <p className="text-sm text-muted-foreground">No data</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Holdings table */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">Current Holdings</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {summary ? (
              <SnapshotTable holdings={summary.holdings} />
            ) : (
              <p className="px-6 py-4 text-sm text-muted-foreground">No holdings data</p>
            )}
          </CardContent>
        </Card>

        {/* Projection curve */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium">FIRE Projection</CardTitle>
            <p className="text-xs text-muted-foreground">
              Compound growth · 20yr horizon · €750/mo contribution · FIRE target €500k
            </p>
          </CardHeader>
          <CardContent>
            <ProjectionCurve monthlyContribution={750} targetAmount={500000} />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
