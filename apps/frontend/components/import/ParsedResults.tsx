"use client";

import { AssetBadge } from "@/components/ui/AssetBadge";
import type { AssetType, IngestResponse } from "@/lib/types";

interface ParsedResultsProps {
  result: IngestResponse;
  selectedAssets: Set<number>;
  selectedSnapshots: Set<number>;
  onToggleAsset: (index: number) => void;
  onToggleSnapshot: (index: number) => void;
  resolvedNames: Record<string, string>;
  onResolve: (originalName: string, chosenName: string) => void;
}

export function ParsedResults({
  result,
  selectedAssets,
  selectedSnapshots,
  onToggleAsset,
  onToggleSnapshot,
  resolvedNames,
  onResolve,
}: ParsedResultsProps) {
  return (
    <div className="bg-surface-container-low rounded-xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider">
          Parsed Results
        </h2>
        <span
          className={`px-2.5 py-0.5 rounded-full text-xs font-label ${
            result.is_valid
              ? "bg-primary/10 text-primary"
              : "bg-error/10 text-error"
          }`}
        >
          {result.is_valid ? "Valid" : "Has Errors"}
        </span>
      </div>

      {/* Validation errors */}
      {result.validation_errors.length > 0 && (
        <div className="bg-error/5 rounded-lg p-4 space-y-1">
          {result.validation_errors.map((err, i) => (
            <p key={i} className="text-sm text-error">
              {err}
            </p>
          ))}
        </div>
      )}

      {/* Disambiguation — shown when the LLM found multiple possible existing assets */}
      {result.ambiguous_assets.length > 0 && (
        <div className="bg-surface-container rounded-lg p-4 space-y-4 border border-outline-variant/30">
          <p className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
            Ambiguous matches — select which existing asset was meant
          </p>
          {result.ambiguous_assets.map((amb) => (
            <div key={amb.original_name} className="space-y-2">
              <p className="text-sm text-on-surface">
                <span className="font-medium">"{amb.original_name}"</span> could refer to:
              </p>
              <div className="space-y-1 pl-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name={`resolve-${amb.original_name}`}
                    value="__new__"
                    checked={!(amb.original_name in resolvedNames)}
                    onChange={() => onResolve(amb.original_name, "__new__")}
                    className="h-4 w-4 text-primary"
                  />
                  <span className="text-sm text-on-surface-variant italic">
                    Create as new asset: "{amb.original_name}"
                  </span>
                </label>
                {amb.candidates.map((candidate) => (
                  <label key={candidate} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name={`resolve-${amb.original_name}`}
                      value={candidate}
                      checked={resolvedNames[amb.original_name] === candidate}
                      onChange={() => onResolve(amb.original_name, candidate)}
                      className="h-4 w-4 text-primary"
                    />
                    <span className="text-sm text-on-surface font-medium">{candidate}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Validated assets */}
      {result.validated_assets.length > 0 && (
        <div>
          <h3 className="text-xs font-label text-on-surface-variant uppercase tracking-wider mb-3">
            Assets ({selectedAssets.size}/{result.validated_assets.length})
          </h3>
          <div className="space-y-2">
            {result.validated_assets.map((asset, i) => (
              <label
                key={i}
                className="flex items-center justify-between bg-surface-container rounded-lg p-3 cursor-pointer hover:bg-surface-container-high/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={selectedAssets.has(i)}
                    onChange={() => onToggleAsset(i)}
                    className="h-4 w-4 rounded border-outline text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-on-surface font-medium">
                    {String(asset.name ?? "")}
                  </span>
                  {asset.asset_type ? (
                    <AssetBadge type={String(asset.asset_type) as AssetType} />
                  ) : null}
                  {asset.ticker ? (
                    <span className="text-xs font-mono text-on-surface-variant">
                      {String(asset.ticker)}
                    </span>
                  ) : null}
                </div>
                {asset.annualized_return_pct != null && (
                  <span className="text-xs font-mono text-on-surface-variant">
                    {String(asset.annualized_return_pct)}
                  </span>
                )}
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Validated snapshots */}
      {result.validated_snapshots.length > 0 && (
        <div>
          <h3 className="text-xs font-label text-on-surface-variant uppercase tracking-wider mb-3">
            Snapshots ({selectedSnapshots.size}/{result.validated_snapshots.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="text-xs font-label text-on-surface-variant uppercase tracking-wider text-left px-3 py-2 w-8">
                  </th>
                  <th className="text-xs font-label text-on-surface-variant uppercase tracking-wider text-left px-3 py-2">
                    Asset
                  </th>
                  <th className="text-xs font-label text-on-surface-variant uppercase tracking-wider text-left px-3 py-2">
                    Date
                  </th>
                  <th className="text-xs font-label text-on-surface-variant uppercase tracking-wider text-right px-3 py-2">
                    Balance
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.validated_snapshots.map((snap, i) => (
                  <tr
                    key={i}
                    className="hover:bg-surface-container-high/30 transition-colors cursor-pointer"
                    onClick={() => onToggleSnapshot(i)}
                  >
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selectedSnapshots.has(i)}
                        onChange={() => onToggleSnapshot(i)}
                        className="h-4 w-4 rounded border-outline text-primary focus:ring-primary"
                      />
                    </td>
                    <td className="px-3 py-2 text-sm text-on-surface">
                      {String(snap.asset_name ?? snap.name ?? "")}
                    </td>
                    <td className="px-3 py-2 text-sm font-mono text-on-surface-variant">
                      {String(snap.snapshot_date ?? "")}
                    </td>
                    <td className="px-3 py-2 text-sm font-mono text-on-surface text-right">
                      {String(snap.balance ?? "")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
