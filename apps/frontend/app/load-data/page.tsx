"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  getAuthStatus,
  loadRealData,
  logout,
  type LoadSummary,
  type LoadAssetEntry,
  type LoadSnapshotEntry,
} from "@/lib/api";
import { parseCsv, readFileAsText } from "@/lib/csv";
import { CANONICAL_ASSET_TYPES, suggestAssetType } from "@/lib/assetTypes";
import type { AssetType } from "@/lib/types";

interface Draft {
  original_name: string;
  name: string;
  asset_type: AssetType;
  annualized_return_pct: string;
  snapshot_count: number;
}

export default function LoadDataPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [checking, setChecking] = useState(true);
  const [assetsFile, setAssetsFile] = useState<File | null>(null);
  const [snapshotsFile, setSnapshotsFile] = useState<File | null>(null);
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [snapshots, setSnapshots] = useState<LoadSnapshotEntry[]>([]);
  const [parseError, setParseError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState<LoadSummary | null>(null);

  useEffect(() => {
    getAuthStatus()
      .then((s) => {
        if (!s.authenticated) router.replace("/login");
        else setChecking(false);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  const unmatched = useMemo(() => {
    if (!drafts) return [];
    const known = new Set(drafts.map((d) => d.original_name));
    const missing = new Set<string>();
    for (const s of snapshots) {
      if (!known.has(s.asset_name)) missing.add(s.asset_name);
    }
    return Array.from(missing);
  }, [drafts, snapshots]);

  if (checking) return <div className="py-16 text-on-surface-variant">Checking session…</div>;

  async function handlePreview(e: React.FormEvent) {
    e.preventDefault();
    if (!assetsFile || !snapshotsFile) return;
    setParseError("");
    try {
      const [assetsText, snapshotsText] = await Promise.all([
        readFileAsText(assetsFile),
        readFileAsText(snapshotsFile),
      ]);
      const assetsRows = parseCsv(assetsText);
      const snapshotRows = parseCsv(snapshotsText);

      if (!assetsRows.length) throw new Error("Assets CSV has no data rows.");
      if (!snapshotRows.length) throw new Error("Snapshots CSV has no data rows.");

      const snapshotEntries: LoadSnapshotEntry[] = snapshotRows.map((r, i) => {
        const asset_name = (r["asset_name"] ?? "").trim();
        const snapshot_date = (r["snapshot_date"] ?? "").trim();
        const balance = (r["balance"] ?? "").trim();
        if (!asset_name || !snapshot_date || !balance) {
          throw new Error(`Snapshots row ${i + 2}: missing asset_name/snapshot_date/balance.`);
        }
        return { asset_name, snapshot_date, balance };
      });

      const countsByName = new Map<string, number>();
      for (const s of snapshotEntries) {
        countsByName.set(s.asset_name, (countsByName.get(s.asset_name) ?? 0) + 1);
      }

      const newDrafts: Draft[] = assetsRows.map((r, i) => {
        const name = (r["name"] ?? "").trim();
        if (!name) throw new Error(`Assets row ${i + 2}: missing name.`);
        const rawType = (r["asset_type"] ?? "").trim();
        const ret = (r["annualized_return_pct"] ?? "").trim();
        return {
          original_name: name,
          name,
          asset_type: suggestAssetType(rawType),
          annualized_return_pct: ret,
          snapshot_count: countsByName.get(name) ?? 0,
        };
      });

      setDrafts(newDrafts);
      setSnapshots(snapshotEntries);
      setSummary(null);
      setError("");
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "Parse failed");
      setDrafts(null);
      setSnapshots([]);
    }
  }

  function updateDraft(i: number, patch: Partial<Draft>) {
    setDrafts((prev) => {
      if (!prev) return prev;
      const next = [...prev];
      next[i] = { ...next[i], ...patch };
      return next;
    });
  }

  async function handleSubmit() {
    if (!drafts) return;
    setSubmitting(true);
    setError("");
    try {
      const payloadAssets: LoadAssetEntry[] = drafts.map((d) => {
        const ret = d.annualized_return_pct.trim();
        return {
          original_name: d.original_name,
          name: d.name.trim(),
          asset_type: d.asset_type,
          annualized_return_pct: ret === "" ? null : ret,
        };
      });
      const result = await loadRealData({ assets: payloadAssets, snapshots });
      setSummary(result);
      queryClient.invalidateQueries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    await logout();
    queryClient.invalidateQueries();
    router.push("/");
  }

  function reset() {
    setDrafts(null);
    setSnapshots([]);
    setSummary(null);
    setError("");
  }

  return (
    <div className="py-8 max-w-5xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-headline font-bold tracking-tight">
            Load real portfolio data
          </h1>
          <p className="text-sm text-on-surface-variant mt-1">
            Upload two CSVs, map each asset to a canonical type, then submit.
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="px-3 py-1.5 text-sm rounded-lg border border-outline-variant/30 text-on-surface-variant hover:text-on-surface"
        >
          Log out
        </button>
      </div>

      {!drafts && (
        <form onSubmit={handlePreview} className="space-y-4">
          <label className="block">
            <span className="text-sm font-label text-on-surface-variant">Assets CSV</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setAssetsFile(e.target.files?.[0] ?? null)}
              className="mt-1 block w-full text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm font-label text-on-surface-variant">Snapshots CSV</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setSnapshotsFile(e.target.files?.[0] ?? null)}
              className="mt-1 block w-full text-sm"
            />
          </label>

          {parseError && (
            <div className="text-sm text-error bg-error/5 rounded-lg px-3 py-2">{parseError}</div>
          )}

          <button
            type="submit"
            disabled={!assetsFile || !snapshotsFile}
            className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label disabled:opacity-50"
          >
            Preview & map
          </button>
        </form>
      )}

      {drafts && (
        <div className="space-y-4">
          <div className="text-sm text-on-surface-variant">
            {drafts.length} assets · {snapshots.length} snapshots.
            Edit name, pick a category, adjust return.
          </div>

          {unmatched.length > 0 && (
            <div className="text-sm bg-tertiary-container/20 border border-tertiary/30 rounded-lg px-3 py-2">
              <strong>Snapshots reference unknown asset names:</strong>{" "}
              {unmatched.join(", ")}. Rename an asset below to match, or these
              snapshots will be skipped.
            </div>
          )}

          <div className="overflow-x-auto border border-outline-variant/20 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-surface-container">
                <tr className="text-left">
                  <th className="px-3 py-2 font-label">Name</th>
                  <th className="px-3 py-2 font-label">Category</th>
                  <th className="px-3 py-2 font-label">Annualized return</th>
                  <th className="px-3 py-2 font-label">Snapshots</th>
                </tr>
              </thead>
              <tbody>
                {drafts.map((d, i) => (
                  <tr key={d.original_name} className="border-t border-outline-variant/10">
                    <td className="px-3 py-1.5">
                      <input
                        value={d.name}
                        onChange={(e) => updateDraft(i, { name: e.target.value })}
                        className="w-full bg-transparent px-2 py-1 rounded border border-outline-variant/30"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={d.asset_type}
                        onChange={(e) =>
                          updateDraft(i, { asset_type: e.target.value as AssetType })
                        }
                        className="bg-transparent px-2 py-1 rounded border border-outline-variant/30"
                      >
                        {CANONICAL_ASSET_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        value={d.annualized_return_pct}
                        onChange={(e) =>
                          updateDraft(i, { annualized_return_pct: e.target.value })
                        }
                        placeholder="e.g. 0.085"
                        className="w-28 bg-transparent px-2 py-1 rounded border border-outline-variant/30"
                      />
                    </td>
                    <td className="px-3 py-1.5 text-on-surface-variant">{d.snapshot_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {error && (
            <div className="text-sm text-error bg-error/5 rounded-lg px-3 py-2">{error}</div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label disabled:opacity-50"
            >
              {submitting ? "Uploading…" : "Submit"}
            </button>
            <button
              onClick={reset}
              disabled={submitting}
              className="px-4 py-2 rounded-lg border border-outline-variant/30 text-on-surface-variant"
            >
              Start over
            </button>
          </div>
        </div>
      )}

      {summary && (
        <div className="mt-6 bg-surface-container rounded-lg p-4 text-sm space-y-1">
          <div>Assets loaded: <strong>{summary.assets_loaded}</strong></div>
          <div>Snapshots loaded: <strong>{summary.snapshots_loaded}</strong></div>
          {summary.skipped.length > 0 && (
            <details className="mt-2">
              <summary className="cursor-pointer text-on-surface-variant">
                {summary.skipped.length} skipped
              </summary>
              <ul className="mt-2 list-disc list-inside text-on-surface-variant">
                {summary.skipped.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
