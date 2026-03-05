import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProjectionCurve } from "@/components/dashboard/ProjectionCurve";
import Link from "next/link";

export default function ProjectionsPage() {
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
          <span className="font-medium">Projections</span>
        </nav>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8 space-y-6">
        <div>
          <h2 className="text-2xl font-bold">FIRE Projections</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Deterministic compound growth — Phase 2 adds Monte Carlo simulation
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">20-Year Projection · €750/mo</CardTitle>
            <p className="text-xs text-muted-foreground">
              Allocation-weighted real returns · 2% inflation adjusted
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
