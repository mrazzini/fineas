"use client";

import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestText, applyIngest } from "@/lib/api";
import { InputPanel } from "@/components/import/InputPanel";
import { ParsedResults } from "@/components/import/ParsedResults";
import { ConfirmBar } from "@/components/import/ConfirmBar";
import type { IngestResponse } from "@/lib/types";

export default function ImportPage() {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [confirmError, setConfirmError] = useState("");

  // ── Selection state ────────────────────────────────────────────────────
  const [selectedAssets, setSelectedAssets] = useState<Set<number>>(new Set());
  const [selectedSnapshots, setSelectedSnapshots] = useState<Set<number>>(new Set());

  const toggleAsset = useCallback((index: number) => {
    setSelectedAssets((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const toggleSnapshot = useCallback((index: number) => {
    setSelectedSnapshots((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  // ── Parse mutation ─────────────────────────────────────────────────────
  const parseMutation = useMutation({
    mutationFn: () => ingestText({ text }),
    onSuccess: (data) => {
      setResult(data);
      setConfirmError("");
      // Select all items by default
      setSelectedAssets(new Set(data.validated_assets.map((_, i) => i)));
      setSelectedSnapshots(new Set(data.validated_snapshots.map((_, i) => i)));
    },
  });

  // ── Confirm (apply) ────────────────────────────────────────────────────
  const [isConfirming, setIsConfirming] = useState(false);

  const handleConfirm = async () => {
    if (!result || !result.is_valid) return;
    setIsConfirming(true);
    setConfirmError("");

    try {
      // Filter to only selected items
      const assets = result.validated_assets.filter((_, i) => selectedAssets.has(i));
      const snapshots = result.validated_snapshots.filter((_, i) => selectedSnapshots.has(i));

      const response = await applyIngest({
        validated_assets: assets,
        validated_snapshots: snapshots,
      });

      if (!response.success) {
        setConfirmError(
          `Partial errors: ${response.apply_errors.join("; ")}`
        );
      }

      // Refresh asset-related queries
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["latestBalances"] });
      setResult(null);
      setText("");
    } catch (err: unknown) {
      setConfirmError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setIsConfirming(false);
    }
  };

  const handleDiscard = () => {
    setResult(null);
    setConfirmError("");
  };

  const hasSelection = selectedAssets.size > 0 || selectedSnapshots.size > 0;

  return (
    <div className={`py-8 space-y-6 ${result ? "pb-24" : ""}`}>
      <div>
        <h1 className="text-2xl font-headline font-bold tracking-tight">
          Smart Import
        </h1>
        <p className="text-sm text-on-surface-variant mt-1">
          Paste portfolio data and let AI parse it into structured records
        </p>
      </div>

      <InputPanel
        text={text}
        onTextChange={setText}
        onParse={() => parseMutation.mutate()}
        isParsing={parseMutation.isPending}
      />

      {parseMutation.isError && (
        <div className="bg-error/5 rounded-lg p-4">
          <p className="text-sm text-error">
            {parseMutation.error.message}
          </p>
        </div>
      )}

      {result && (
        <ParsedResults
          result={result}
          selectedAssets={selectedAssets}
          selectedSnapshots={selectedSnapshots}
          onToggleAsset={toggleAsset}
          onToggleSnapshot={toggleSnapshot}
        />
      )}

      {confirmError && (
        <div className="bg-error/5 rounded-lg p-4">
          <p className="text-sm text-error">{confirmError}</p>
        </div>
      )}

      {result && (
        <ConfirmBar
          onDiscard={handleDiscard}
          onConfirm={handleConfirm}
          isConfirming={isConfirming}
          disabled={!result.is_valid || !hasSelection}
        />
      )}
    </div>
  );
}
