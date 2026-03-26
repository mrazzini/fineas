"use client";

import Link from "next/link";
import { AssetBadge } from "@/components/ui/AssetBadge";
import { formatEUR, formatPercent } from "@/lib/format";
import type { Asset, Snapshot } from "@/lib/types";

interface AssetHeaderProps {
  asset: Asset;
  latestSnapshot: Snapshot | null;
  firstSnapshot: Snapshot | null;
}

export function AssetHeader({ asset, latestSnapshot, firstSnapshot }: AssetHeaderProps) {
  const balance = latestSnapshot ? parseFloat(latestSnapshot.balance) : 0;
  const initial = firstSnapshot ? parseFloat(firstSnapshot.balance) : 0;
  const gain = balance - initial;
  const gainPct = initial > 0 ? gain / initial : 0;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-on-surface-variant mb-4">
        <Link href="/assets" className="hover:text-on-surface transition-colors">
          Assets
        </Link>
        <span>/</span>
        <span className="text-on-surface">{asset.name}</span>
      </div>

      {/* Header card */}
      <div className="bg-surface-container-low rounded-xl p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-headline font-bold tracking-tight">
                {asset.name}
              </h1>
              <AssetBadge type={asset.asset_type} />
            </div>
            {asset.ticker && (
              <p className="text-sm font-mono text-on-surface-variant">
                {asset.ticker}
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-surface-container rounded-lg p-4">
            <p className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
              Balance
            </p>
            <p className="text-xl font-mono font-bold text-on-surface mt-1">
              {formatEUR(balance)}
            </p>
          </div>
          <div className="bg-surface-container rounded-lg p-4">
            <p className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
              Annual Return
            </p>
            <p className="text-xl font-mono font-bold text-on-surface mt-1">
              {asset.annualized_return_pct
                ? formatPercent(asset.annualized_return_pct)
                : "—"}
            </p>
          </div>
          <div className="bg-surface-container rounded-lg p-4">
            <p className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
              Total Gain
            </p>
            <p
              className={`text-xl font-mono font-bold mt-1 ${
                gain >= 0 ? "text-primary" : "text-error"
              }`}
            >
              {gain >= 0 ? "+" : ""}
              {formatEUR(gain)}
              <span className="text-sm ml-1">
                ({gainPct >= 0 ? "+" : ""}{(gainPct * 100).toFixed(1)}%)
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
