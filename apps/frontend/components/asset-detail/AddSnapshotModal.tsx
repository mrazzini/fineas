"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GlassModal } from "@/components/ui/GlassModal";
import { upsertSnapshot } from "@/lib/api";

interface AddSnapshotModalProps {
  open: boolean;
  onClose: () => void;
  assetId: string;
}

export function AddSnapshotModal({ open, onClose, assetId }: AddSnapshotModalProps) {
  const queryClient = useQueryClient();
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [balance, setBalance] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: { snapshot_date: string; balance: string }) =>
      upsertSnapshot(assetId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["snapshots", assetId] });
      queryClient.invalidateQueries({ queryKey: ["latestBalances"] });
      setBalance("");
      setError("");
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!balance.trim()) return;
    mutation.mutate({ snapshot_date: date, balance: balance.trim() });
  };

  return (
    <GlassModal open={open} onClose={onClose} title="Add Snapshot">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
            Date
          </label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
            Balance
          </label>
          <input
            type="text"
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
            className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
            placeholder="12500.00"
            required
          />
        </div>

        {error && <p className="text-xs text-error">{error}</p>}

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-on-surface-variant hover:text-on-surface transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 rounded-lg text-sm font-medium liquid-gradient text-on-primary disabled:opacity-50"
          >
            {mutation.isPending ? "Saving..." : "Save Snapshot"}
          </button>
        </div>
      </form>
    </GlassModal>
  );
}
