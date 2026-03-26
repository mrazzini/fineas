"use client";

import { useQuery } from "@tanstack/react-query";
import { getAssets, getSnapshots, getProjection } from "@/lib/api";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { ProjectionChart } from "@/components/dashboard/ProjectionChart";
import { TopAssetsTable } from "@/components/dashboard/TopAssetsTable";
import { AllocationDonut } from "@/components/dashboard/AllocationDonut";
import type { Snapshot } from "@/lib/types";

const MONTHLY_CONTRIBUTION = 1200;
const ANNUAL_EXPENSES = 30000;
const PROJECTION_MONTHS = 300;

export default function DashboardPage() {
  const { data: assets = [] } = useQuery({
    queryKey: ["assets"],
    queryFn: () => getAssets(),
  });

  const { data: projection } = useQuery({
    queryKey: ["projection", MONTHLY_CONTRIBUTION, ANNUAL_EXPENSES],
    queryFn: () =>
      getProjection({
        months: PROJECTION_MONTHS,
        monthly_contribution: MONTHLY_CONTRIBUTION,
        annual_expenses: ANNUAL_EXPENSES,
      }),
  });

  // Fetch latest snapshot per asset for balance display
  const { data: latestBalances = {} } = useQuery({
    queryKey: ["latestBalances", assets.map((a) => a.id)],
    enabled: assets.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        assets.map(async (a) => {
          const snaps = await getSnapshots(a.id);
          const latest = snaps.length > 0 ? snaps[snaps.length - 1] : null;
          return [a.id, latest] as [string, Snapshot | null];
        })
      );
      return Object.fromEntries(entries) as Record<string, Snapshot | null>;
    },
  });

  if (!projection) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const fireTarget = projection.fire_target
    ? parseFloat(projection.fire_target)
    : null;

  return (
    <div className="py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-headline font-bold tracking-tight">
          Dashboard
        </h1>
        <p className="text-sm text-on-surface-variant mt-1">
          Portfolio overview and FIRE projection
        </p>
      </div>

      <KpiRow
        projection={projection}
        monthlyContribution={MONTHLY_CONTRIBUTION}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ProjectionChart
            monthly={projection.monthly}
            fireTarget={fireTarget}
          />
        </div>
        <AllocationDonut assets={assets} latestBalances={latestBalances} />
      </div>

      <TopAssetsTable assets={assets} latestBalances={latestBalances} />
    </div>
  );
}
