"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GlassModal } from "@/components/ui/GlassModal";
import { createAsset } from "@/lib/api";
import { ALL_ASSET_TYPES, ASSET_TYPE_LABELS } from "@/lib/constants";
import type { AssetType } from "@/lib/types";

interface AddAssetModalProps {
  open: boolean;
  onClose: () => void;
}

export function AddAssetModal({ open, onClose }: AddAssetModalProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("STOCKS");
  const [ticker, setTicker] = useState("");
  const [returnPct, setReturnPct] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: createAsset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setName("");
      setTicker("");
      setReturnPct("");
      setError("");
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message.includes("409") ? "Asset with this name already exists" : err.message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    mutation.mutate({
      name: name.trim(),
      asset_type: assetType,
      ticker: ticker.trim() || null,
      annualized_return_pct: returnPct ? returnPct : null,
    });
  };

  return (
    <GlassModal open={open} onClose={onClose} title="Add Asset">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
            placeholder="e.g. VWCE ETF"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
            Type
          </label>
          <select
            value={assetType}
            onChange={(e) => setAssetType(e.target.value as AssetType)}
            className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
          >
            {ALL_ASSET_TYPES.map((t) => (
              <option key={t} value={t}>
                {ASSET_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
              Ticker
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="VWCE"
            />
          </div>
          <div>
            <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
              Annual Return
            </label>
            <input
              type="text"
              value={returnPct}
              onChange={(e) => setReturnPct(e.target.value)}
              className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="0.085"
            />
          </div>
        </div>

        {error && (
          <p className="text-xs text-error">{error}</p>
        )}

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
            {mutation.isPending ? "Adding..." : "Add Asset"}
          </button>
        </div>
      </form>
    </GlassModal>
  );
}
