"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { getAuthStatus, loadRealData, logout, type LoadSummary } from "@/lib/api";

export default function LoadDataPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [checking, setChecking] = useState(true);
  const [assetsFile, setAssetsFile] = useState<File | null>(null);
  const [snapshotsFile, setSnapshotsFile] = useState<File | null>(null);
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

  if (checking) return <div className="py-16 text-on-surface-variant">Checking session…</div>;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!assetsFile || !snapshotsFile) return;
    setSubmitting(true);
    setError("");
    setSummary(null);
    try {
      const result = await loadRealData(assetsFile, snapshotsFile);
      setSummary(result);
      queryClient.invalidateQueries();
    } catch (err: unknown) {
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

  return (
    <div className="py-8 max-w-2xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-headline font-bold tracking-tight">
            Load real portfolio data
          </h1>
          <p className="text-sm text-on-surface-variant mt-1">
            Upload two CSVs matching the schema of <code>data/example_*.csv</code>.
            Existing real-data rows are upserted.
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="px-3 py-1.5 text-sm rounded-lg border border-outline-variant/30 text-on-surface-variant hover:text-on-surface"
        >
          Log out
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
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

        {error && (
          <div className="text-sm text-error bg-error/5 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || !assetsFile || !snapshotsFile}
          className="px-4 py-2 rounded-lg bg-primary text-on-primary font-label disabled:opacity-50"
        >
          {submitting ? "Uploading…" : "Upload"}
        </button>
      </form>

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
