"use client";

import Link from "next/link";
import { AssetBadge } from "@/components/ui/AssetBadge";
import { formatEUR } from "@/lib/format";
import type { Asset, Snapshot } from "@/lib/types";

interface TopAssetsTableProps {
  assets: Asset[];
  latestBalances: Record<string, Snapshot | null>;
}

export function TopAssetsTable({ assets, latestBalances }: TopAssetsTableProps) {
  const sorted = [...assets]
    .map((a) => ({
      asset: a,
      balance: latestBalances[a.id]
        ? parseFloat(latestBalances[a.id]!.balance)
        : 0,
    }))
    .sort((a, b) => b.balance - a.balance)
    .slice(0, 5);

  return (
    <div className="bg-surface-container-low rounded-xl p-6">
      <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider mb-4">
        Top Assets
      </h2>
      <div className="space-y-3">
        {sorted.map(({ asset, balance }) => (
          <Link
            key={asset.id}
            href={`/assets/${asset.id}`}
            className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-surface-container-high/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm font-body text-on-surface">
                {asset.name}
              </span>
              <AssetBadge type={asset.asset_type} />
            </div>
            <span className="font-mono text-sm text-on-surface">
              {formatEUR(balance)}
            </span>
          </Link>
        ))}
        {sorted.length === 0 && (
          <p className="text-sm text-on-surface-variant text-center py-4">
            No assets yet
          </p>
        )}
      </div>
    </div>
  );
}
