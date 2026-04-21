"use client";

import { useState } from "react";
import { useAssets, useIsOwner, useLatestBalances } from "@/lib/hooks";
import { AssetTable } from "@/components/assets/AssetTable";
import { AddAssetModal } from "@/components/assets/AddAssetModal";

export default function AssetsPage() {
  const [showModal, setShowModal] = useState(false);
  const isOwner = useIsOwner();
  const { data: assets = [] } = useAssets();
  const { data: latestBalances = {} } = useLatestBalances(assets);

  return (
    <div className="py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-headline font-bold tracking-tight">
            Assets
          </h1>
          <p className="text-sm text-on-surface-variant mt-1">
            {isOwner
              ? "Manage your portfolio assets"
              : "Demo portfolio — log in to manage your own"}
          </p>
        </div>
        {isOwner && (
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 rounded-lg text-sm font-medium liquid-gradient text-on-primary"
          >
            + Add Asset
          </button>
        )}
      </div>

      <AssetTable assets={assets} latestBalances={latestBalances} />
      <AddAssetModal open={showModal} onClose={() => setShowModal(false)} />
    </div>
  );
}
