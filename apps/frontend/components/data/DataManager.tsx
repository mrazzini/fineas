"use client";

import { useState, useEffect } from "react";
import type { Asset, Snapshot } from "@/types/schema";
import {
  getSnapshotsForAsset,
  addSnapshot,
  updateSnapshot,
  deleteSnapshot,
  updateAsset,
} from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Props {
  assets: Asset[];
}

const formatEUR = (v: number) =>
  new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
  }).format(v);

export function DataManager({ assets: initialAssets }: Props) {
  const [assets, setAssets] = useState<Asset[]>(initialAssets);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [addDate, setAddDate] = useState("");
  const [addAmount, setAddAmount] = useState("");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDate, setEditDate] = useState("");
  const [editAmount, setEditAmount] = useState("");

  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedAsset) return;
    setLoading(true);
    setFetchError(null);
    getSnapshotsForAsset(selectedAsset.id)
      .then(setSnapshots)
      .catch((e) => setFetchError(String(e)))
      .finally(() => setLoading(false));
  }, [selectedAsset]);

  const reload = () => {
    if (!selectedAsset) return;
    getSnapshotsForAsset(selectedAsset.id).then(setSnapshots);
  };

  const handleToggleAsset = async (a: Asset) => {
    const updated = await updateAsset(a.id, { is_active: !a.is_active });
    setAssets((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    // If we just deactivated the selected asset, clear snapshot panel
    if (selectedAsset?.id === a.id && !updated.is_active) {
      setSelectedAsset(null);
      setSnapshots([]);
    }
  };

  const handleAdd = async () => {
    if (!selectedAsset || !addDate || !addAmount) return;
    await addSnapshot({
      asset_id: selectedAsset.id,
      date: addDate,
      amount: parseFloat(addAmount),
    });
    setShowAddForm(false);
    setAddDate("");
    setAddAmount("");
    reload();
  };

  const handleEditSave = async (snap: Snapshot) => {
    await updateSnapshot(snap.id, {
      asset_id: snap.asset_id,
      date: editDate,
      amount: parseFloat(editAmount),
    });
    setEditingId(null);
    reload();
  };

  const handleDelete = async (id: string) => {
    await deleteSnapshot(id);
    setDeletingId(null);
    reload();
  };

  return (
    <div className="flex gap-6">
      {/* Asset list */}
      <div className="w-56 shrink-0">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Assets</h3>
        <ul className="space-y-1">
          {assets.map((a) => (
            <li key={a.id}>
              <div className="flex items-center justify-between rounded-md">
                <button
                  onClick={() => {
                    setSelectedAsset(a);
                    setShowAddForm(false);
                    setEditingId(null);
                    setDeletingId(null);
                  }}
                  className={`flex-1 text-left text-sm px-3 py-2 rounded-md transition-colors ${
                    !a.is_active ? "opacity-50 text-muted-foreground" : ""
                  } ${
                    selectedAsset?.id === a.id
                      ? "bg-slate-900 text-white"
                      : "hover:bg-slate-100"
                  }`}
                >
                  {a.name}
                </button>
                <button
                  onClick={() => handleToggleAsset(a)}
                  className="text-xs text-muted-foreground hover:text-foreground ml-1 px-1"
                  title={a.is_active ? "Deactivate" : "Activate"}
                >
                  {a.is_active ? "✕" : "↺"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* Snapshot panel */}
      <div className="flex-1 min-w-0">
        {!selectedAsset ? (
          <p className="text-sm text-muted-foreground pt-2">
            Select an asset to view snapshots.
          </p>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium">{selectedAsset.name}</h3>
              <button
                onClick={() => setShowAddForm((v) => !v)}
                className="text-sm px-3 py-1 border rounded-md hover:bg-slate-50"
              >
                {showAddForm ? "Cancel" : "Add Snapshot"}
              </button>
            </div>

            {showAddForm && (
              <div className="flex gap-2 mb-4 p-3 border rounded-md bg-slate-50">
                <input
                  type="date"
                  value={addDate}
                  onChange={(e) => setAddDate(e.target.value)}
                  className="border rounded px-2 py-1 text-sm"
                />
                <input
                  type="number"
                  placeholder="Amount (€)"
                  value={addAmount}
                  onChange={(e) => setAddAmount(e.target.value)}
                  className="border rounded px-2 py-1 text-sm w-32"
                />
                <button
                  onClick={handleAdd}
                  className="text-sm px-3 py-1 bg-slate-900 text-white rounded-md hover:bg-slate-700"
                >
                  Save
                </button>
              </div>
            )}

            {loading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : fetchError ? (
              <p className="text-sm text-red-500">Error: {fetchError}</p>
            ) : snapshots.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No snapshots for this asset.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snapshots.map((snap) => (
                    <TableRow key={snap.id}>
                      <TableCell>
                        {editingId === snap.id ? (
                          <input
                            type="date"
                            value={editDate}
                            onChange={(e) => setEditDate(e.target.value)}
                            className="border rounded px-2 py-1 text-sm"
                          />
                        ) : (
                          snap.date
                        )}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {editingId === snap.id ? (
                          <input
                            type="number"
                            value={editAmount}
                            onChange={(e) => setEditAmount(e.target.value)}
                            className="border rounded px-2 py-1 text-sm w-28 text-right"
                          />
                        ) : (
                          formatEUR(snap.amount)
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {snap.source}
                      </TableCell>
                      <TableCell className="text-right">
                        {deletingId === snap.id ? (
                          <span className="text-xs">
                            Delete?{" "}
                            <button
                              onClick={() => handleDelete(snap.id)}
                              className="text-red-600 font-medium hover:underline"
                            >
                              Yes
                            </button>{" "}
                            <button
                              onClick={() => setDeletingId(null)}
                              className="text-muted-foreground hover:underline"
                            >
                              No
                            </button>
                          </span>
                        ) : editingId === snap.id ? (
                          <span className="text-xs space-x-2">
                            <button
                              onClick={() => handleEditSave(snap)}
                              className="text-emerald-600 font-medium hover:underline"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="text-muted-foreground hover:underline"
                            >
                              Cancel
                            </button>
                          </span>
                        ) : (
                          <span className="text-xs space-x-2">
                            <button
                              onClick={() => {
                                setEditingId(snap.id);
                                setEditDate(snap.date);
                                setEditAmount(String(snap.amount));
                                setDeletingId(null);
                              }}
                              className="text-blue-600 hover:underline"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => {
                                setDeletingId(snap.id);
                                setEditingId(null);
                              }}
                              className="text-red-500 hover:underline"
                            >
                              Delete
                            </button>
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </div>
    </div>
  );
}
