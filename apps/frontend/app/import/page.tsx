"use client";

import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestText, applyIngest } from "@/lib/api";
import { useAssets, useIsOwner, useLatestBalances } from "@/lib/hooks";
import { InputPanel } from "@/components/import/InputPanel";
import { ParsedResults } from "@/components/import/ParsedResults";
import { ConfirmBar } from "@/components/import/ConfirmBar";
import type { ExistingAssetHint, IngestResponse } from "@/lib/types";


export default function ImportPage() {
  const queryClient = useQueryClient();
  const isOwner = useIsOwner();
  const { data: assets = [] } = useAssets();
  const { data: latestBalances = {} } = useLatestBalances(assets);
  const [text, setText] = useState("");
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [confirmError, setConfirmError] = useState("");

  // ── Selection state ────────────────────────────────────────────────────
  const [selectedAssets, setSelectedAssets] = useState<Set<number>>(new Set());
  const [selectedSnapshots, setSelectedSnapshots] = useState<Set<number>>(new Set());
  const [resolvedNames, setResolvedNames] = useState<Record<string, string>>({});

  const handleResolve = useCallback((originalName: string, chosenName: string) => {
    setResolvedNames((prev) => {
      const next = { ...prev };
      if (chosenName === "__new__") {
        delete next[originalName];
      } else {
        next[originalName] = chosenName;
      }
      return next;
    });
  }, []);

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
    mutationFn: () => {
      const existing_assets: ExistingAssetHint[] = assets.map((a) => ({
        name: a.name,
        asset_type: a.asset_type,
        ticker: a.ticker,
        latest_balance: latestBalances[a.id]
          ? parseFloat(latestBalances[a.id]!.balance)
          : null,
      }));
      return ingestText({ text, existing_assets });
    },
    onSuccess: (data) => {
      setResult(data);
      setConfirmError("");
      setResolvedNames({});
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
        resolved_names: Object.fromEntries(
          Object.entries(resolvedNames).filter(([, v]) => v !== "__new__")
        ),
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
    setResolvedNames({});
  };

  const hasSelection = selectedAssets.size > 0 || selectedSnapshots.size > 0;
  const canConfirm = isOwner && result?.is_valid && hasSelection;

  return (
    <div className={`py-8 space-y-6 ${result ? "pb-24" : ""}`}>
      <div>
        <h1 className="text-2xl font-headline font-bold tracking-tight">
          Smart Import
        </h1>
        <p className="text-sm text-on-surface-variant mt-1">
          Paste portfolio data and let AI parse it into structured records
        </p>
        {!isOwner && (
          <p className="text-xs text-on-surface-variant mt-2">
            Parsing is open to everyone. Saving parsed results requires owner
            login.
          </p>
        )}
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
          resolvedNames={resolvedNames}
          onResolve={handleResolve}
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
          disabled={!canConfirm}
        />
      )}
    </div>
  );
}
