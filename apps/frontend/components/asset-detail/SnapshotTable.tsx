"use client";

import { DataTable } from "@/components/ui/DataTable";
import { formatEUR, formatDate } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

interface SnapshotTableProps {
  snapshots: Snapshot[];
}

export function SnapshotTable({ snapshots }: SnapshotTableProps) {
  // Most recent first for the table
  const sorted = [...snapshots].reverse();

  const columns = [
    {
      key: "date",
      header: "Date",
      render: (s: Snapshot) => (
        <span className="text-on-surface">{formatDate(s.snapshot_date)}</span>
      ),
    },
    {
      key: "balance",
      header: "Balance",
      align: "right" as const,
      mono: true,
      render: (s: Snapshot) => formatEUR(s.balance),
    },
    {
      key: "change",
      header: "Change",
      align: "right" as const,
      mono: true,
      render: (s: Snapshot) => {
        const idx = snapshots.findIndex((x) => x.id === s.id);
        if (idx <= 0) return <span className="text-on-surface-variant">—</span>;
        const prev = parseFloat(snapshots[idx - 1].balance);
        const curr = parseFloat(s.balance);
        const diff = curr - prev;
        const color = diff >= 0 ? "text-primary" : "text-error";
        return (
          <span className={color}>
            {diff >= 0 ? "+" : ""}
            {formatEUR(diff)}
          </span>
        );
      },
    },
  ];

  return (
    <div className="bg-surface-container-low rounded-xl overflow-hidden">
      <div className="px-6 pt-6 pb-2">
        <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider">
          Snapshots
        </h2>
      </div>
      <DataTable
        columns={columns}
        data={sorted}
        keyExtractor={(s) => s.id}
      />
      {sorted.length === 0 && (
        <p className="text-sm text-on-surface-variant text-center py-8">
          No snapshots yet
        </p>
      )}
    </div>
  );
}
