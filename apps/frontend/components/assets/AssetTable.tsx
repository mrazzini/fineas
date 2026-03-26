"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AssetBadge } from "@/components/ui/AssetBadge";
import { FilterPills } from "@/components/ui/FilterPills";
import { DataTable } from "@/components/ui/DataTable";
import { formatEUR, formatPercent, formatDate } from "@/lib/format";
import { ALL_ASSET_TYPES, ASSET_TYPE_LABELS } from "@/lib/constants";
import type { Asset, AssetType, Snapshot } from "@/lib/types";

interface AssetTableProps {
  assets: Asset[];
  latestBalances: Record<string, Snapshot | null>;
}

const FILTER_OPTIONS = [
  { value: "ALL", label: "All" },
  ...ALL_ASSET_TYPES.map((t) => ({ value: t, label: ASSET_TYPE_LABELS[t] })),
];

export function AssetTable({ assets, latestBalances }: AssetTableProps) {
  const router = useRouter();
  const [filter, setFilter] = useState("ALL");

  const filtered =
    filter === "ALL"
      ? assets
      : assets.filter((a) => a.asset_type === filter);

  const columns = [
    {
      key: "name",
      header: "Name",
      render: (a: Asset) => (
        <span className="text-on-surface font-medium">{a.name}</span>
      ),
    },
    {
      key: "type",
      header: "Type",
      render: (a: Asset) => <AssetBadge type={a.asset_type} />,
    },
    {
      key: "ticker",
      header: "Ticker",
      mono: true,
      render: (a: Asset) => (
        <span className="text-on-surface-variant">{a.ticker || "—"}</span>
      ),
    },
    {
      key: "balance",
      header: "Balance",
      align: "right" as const,
      mono: true,
      render: (a: Asset) => {
        const snap = latestBalances[a.id];
        return snap ? formatEUR(snap.balance) : "—";
      },
    },
    {
      key: "return",
      header: "Return",
      align: "right" as const,
      mono: true,
      render: (a: Asset) =>
        a.annualized_return_pct
          ? formatPercent(a.annualized_return_pct)
          : "—",
    },
    {
      key: "updated",
      header: "Last Updated",
      align: "right" as const,
      render: (a: Asset) => {
        const snap = latestBalances[a.id];
        return (
          <span className="text-on-surface-variant text-xs">
            {snap ? formatDate(snap.snapshot_date) : "—"}
          </span>
        );
      },
    },
  ];

  return (
    <div>
      <div className="mb-4">
        <FilterPills
          options={FILTER_OPTIONS}
          selected={filter}
          onChange={setFilter}
        />
      </div>
      <div className="bg-surface-container-low rounded-xl overflow-hidden">
        <DataTable
          columns={columns}
          data={filtered}
          keyExtractor={(a) => a.id}
          onRowClick={(a) => router.push(`/assets/${a.id}`)}
        />
        {filtered.length === 0 && (
          <p className="text-sm text-on-surface-variant text-center py-8">
            No assets found
          </p>
        )}
      </div>
    </div>
  );
}
