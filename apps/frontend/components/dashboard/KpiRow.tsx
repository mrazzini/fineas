"use client";

import { KpiCard } from "@/components/ui/KpiCard";
import { formatEUR } from "@/lib/format";
import type { ProjectionResponse } from "@/lib/types";

interface KpiRowProps {
  projection: ProjectionResponse;
  monthlyContribution: number;
}

export function KpiRow({ projection, monthlyContribution }: KpiRowProps) {
  const fireTarget = projection.fire_target
    ? parseFloat(projection.fire_target)
    : null;
  const currentTotal = parseFloat(projection.current_total);
  const progress =
    fireTarget && fireTarget > 0
      ? Math.min((currentTotal / fireTarget) * 100, 100)
      : 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard
        label="Net Worth"
        value={formatEUR(projection.current_total)}
        accentColor="bg-primary"
      />
      <KpiCard
        label="FIRE Target"
        value={fireTarget ? formatEUR(fireTarget) : "N/A"}
        accentColor="bg-[#ff716c]"
        subtitle={fireTarget ? `${progress.toFixed(1)}% reached` : undefined}
      />
      <KpiCard
        label="Months to FIRE"
        value={
          projection.months_to_fire != null
            ? String(projection.months_to_fire)
            : "N/A"
        }
        accentColor="bg-[#64B5F6]"
        subtitle={
          projection.fire_date
            ? `Target: ${new Date(projection.fire_date).toLocaleDateString("en-GB", { month: "short", year: "numeric" })}`
            : undefined
        }
      />
      <KpiCard
        label="Monthly Contribution"
        value={formatEUR(monthlyContribution)}
        accentColor="bg-[#CE93D8]"
      />
    </div>
  );
}
