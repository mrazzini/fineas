"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useAsset, useIsOwner, useSnapshots } from "@/lib/hooks";
import { AssetHeader } from "@/components/asset-detail/AssetHeader";
import { BalanceChart } from "@/components/asset-detail/BalanceChart";
import { SnapshotTable } from "@/components/asset-detail/SnapshotTable";
import { AddSnapshotModal } from "@/components/asset-detail/AddSnapshotModal";

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [showModal, setShowModal] = useState(false);
  const isOwner = useIsOwner();

  const { data: asset } = useAsset(id);
  const { data: snapshots = [] } = useSnapshots(id);

  if (!asset) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const latestSnapshot = snapshots.length > 0 ? snapshots[snapshots.length - 1] : null;
  const firstSnapshot = snapshots.length > 0 ? snapshots[0] : null;

  return (
    <div className="py-8 space-y-6">
      <AssetHeader
        asset={asset}
        latestSnapshot={latestSnapshot}
        firstSnapshot={firstSnapshot}
      />

      {isOwner && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 rounded-lg text-sm font-medium liquid-gradient text-on-primary"
          >
            + Add Snapshot
          </button>
        </div>
      )}

      <BalanceChart snapshots={snapshots} />
      <SnapshotTable snapshots={snapshots} />
      {isOwner && (
        <AddSnapshotModal
          open={showModal}
          onClose={() => setShowModal(false)}
          assetId={id}
        />
      )}
    </div>
  );
}
