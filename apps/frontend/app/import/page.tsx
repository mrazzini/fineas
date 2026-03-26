"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestText, getAssets, createAsset, upsertSnapshot } from "@/lib/api";
import { InputPanel } from "@/components/import/InputPanel";
import { ParsedResults } from "@/components/import/ParsedResults";
import { ConfirmBar } from "@/components/import/ConfirmBar";
import type { IngestResponse, AssetCreate } from "@/lib/types";

export default function ImportPage() {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [confirmError, setConfirmError] = useState("");

  const parseMutation = useMutation({
    mutationFn: () => ingestText({ text }),
    onSuccess: (data) => {
      setResult(data);
      setConfirmError("");
    },
  });

  const [isConfirming, setIsConfirming] = useState(false);

  const handleConfirm = async () => {
    if (!result || !result.is_valid) return;
    setIsConfirming(true);
    setConfirmError("");

    try {
      // 1. Get existing assets to match by name
      const existing = await getAssets();
      const nameToId: Record<string, string> = {};
      for (const a of existing) {
        nameToId[a.name.toLowerCase()] = a.id;
      }

      // 2. Create new assets
      for (const rawAsset of result.validated_assets) {
        const name = String(rawAsset.name ?? "");
        if (nameToId[name.toLowerCase()]) continue;

        try {
          const created = await createAsset({
            name,
            asset_type: String(rawAsset.asset_type ?? "OTHER"),
            ticker: rawAsset.ticker ? String(rawAsset.ticker) : null,
            annualized_return_pct: rawAsset.annualized_return_pct
              ? String(rawAsset.annualized_return_pct)
              : null,
          } as AssetCreate);
          nameToId[name.toLowerCase()] = created.id;
        } catch (err: unknown) {
          // 409 = already exists, try to find it
          if (err instanceof Error && err.message.includes("409")) {
            const refreshed = await getAssets();
            const found = refreshed.find(
              (a) => a.name.toLowerCase() === name.toLowerCase()
            );
            if (found) nameToId[name.toLowerCase()] = found.id;
          }
        }
      }

      // 3. Upsert snapshots
      for (const rawSnap of result.validated_snapshots) {
        const assetName = String(
          rawSnap.asset_name ?? rawSnap.name ?? ""
        ).toLowerCase();
        const assetId = nameToId[assetName];
        if (!assetId) continue;

        await upsertSnapshot(assetId, {
          snapshot_date: String(rawSnap.snapshot_date ?? ""),
          balance: String(rawSnap.balance ?? "0"),
        });
      }

      // 4. Done — clear state and refresh
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

      {result && <ParsedResults result={result} />}

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
          disabled={!result.is_valid}
        />
      )}
    </div>
  );
}
