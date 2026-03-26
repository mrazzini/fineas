"use client";

import { DonutChart } from "@/components/charts/DonutChart";
import { ASSET_TYPE_COLORS, ASSET_TYPE_LABELS } from "@/lib/constants";
import { formatEUR } from "@/lib/format";
import type { Asset, AssetType, Snapshot } from "@/lib/types";

interface AllocationDonutProps {
  assets: Asset[];
  latestBalances: Record<string, Snapshot | null>;
}

export function AllocationDonut({ assets, latestBalances }: AllocationDonutProps) {
  const grouped: Record<string, number> = {};
  let total = 0;

  for (const asset of assets) {
    const bal = latestBalances[asset.id]
      ? parseFloat(latestBalances[asset.id]!.balance)
      : 0;
    if (bal <= 0) continue;
    const type = asset.asset_type;
    grouped[type] = (grouped[type] || 0) + bal;
    total += bal;
  }

  const data = Object.entries(grouped).map(([type, value]) => ({
    name: ASSET_TYPE_LABELS[type as AssetType],
    value,
    color: ASSET_TYPE_COLORS[type as AssetType].chart,
  }));

  return (
    <div className="bg-surface-container-low rounded-xl p-6">
      <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider mb-4">
        Allocation
      </h2>
      {data.length > 0 ? (
        <DonutChart
          data={data}
          centerLabel="Total"
          centerValue={formatEUR(total, true)}
        />
      ) : (
        <p className="text-sm text-on-surface-variant text-center py-8">
          No data
        </p>
      )}
    </div>
  );
}
