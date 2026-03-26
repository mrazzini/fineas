"use client";

import { AreaChart } from "@/components/charts/AreaChart";
import type { Snapshot } from "@/lib/types";

interface BalanceChartProps {
  snapshots: Snapshot[];
}

export function BalanceChart({ snapshots }: BalanceChartProps) {
  const data = snapshots.map((s) => ({
    label: new Date(s.snapshot_date).toLocaleDateString("en-GB", {
      month: "short",
      year: "2-digit",
    }),
    value: parseFloat(s.balance),
  }));

  if (data.length === 0) {
    return (
      <div className="bg-surface-container-low rounded-xl p-6 flex items-center justify-center h-48">
        <p className="text-sm text-on-surface-variant">No snapshots yet</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-container-low rounded-xl p-6">
      <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider mb-4">
        Balance History
      </h2>
      <AreaChart data={data} height={280} />
    </div>
  );
}
