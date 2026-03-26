"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAssets, getSnapshots } from "@/lib/api";
import { AssetTable } from "@/components/assets/AssetTable";
import { AddAssetModal } from "@/components/assets/AddAssetModal";
import type { Snapshot } from "@/lib/types";

export default function AssetsPage() {
  const [showModal, setShowModal] = useState(false);

  const { data: assets = [] } = useQuery({
    queryKey: ["assets"],
    queryFn: () => getAssets(),
  });

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

  return (
    <div className="py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-headline font-bold tracking-tight">
            Assets
          </h1>
          <p className="text-sm text-on-surface-variant mt-1">
            Manage your portfolio assets
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 rounded-lg text-sm font-medium liquid-gradient text-on-primary"
        >
          + Add Asset
        </button>
      </div>

      <AssetTable assets={assets} latestBalances={latestBalances} />
      <AddAssetModal open={showModal} onClose={() => setShowModal(false)} />
    </div>
  );
}
