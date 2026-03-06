import type {
  Asset,
  CompoundResult,
  NetWorthHistory,
  PortfolioSummary,
  Snapshot,
} from "@/types/schema";

// Server components run inside the container; client components use relative
// URLs that Next.js rewrites proxy to the backend (see next.config.ts).
const API_BASE =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? "http://localhost:8000")
    : "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} → ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  return apiFetch<PortfolioSummary>("/api/snapshots/latest");
}

export async function getNetWorthHistory(): Promise<NetWorthHistory[]> {
  return apiFetch<NetWorthHistory[]>("/api/snapshots/history");
}

export async function runProjection(params: {
  monthly_contribution: number;
  horizon_years?: number;
  target_amount?: number;
}): Promise<CompoundResult> {
  return apiFetch<CompoundResult>("/api/projections/run", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getAssets(opts?: { includeInactive?: boolean }): Promise<Asset[]> {
  const qs = opts?.includeInactive ? "?include_inactive=true" : "";
  return apiFetch<Asset[]>(`/api/assets/${qs}`);
}

export async function updateAsset(
  id: string,
  payload: { is_active?: boolean },
): Promise<Asset> {
  return apiFetch<Asset>(`/api/assets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getSnapshotsForAsset(assetId: string): Promise<Snapshot[]> {
  return apiFetch<Snapshot[]>(`/api/snapshots/?asset_id=${assetId}`);
}

export async function addSnapshot(payload: {
  asset_id: string;
  date: string;
  amount: number;
  source?: string;
}): Promise<Snapshot> {
  return apiFetch<Snapshot>("/api/snapshots/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSnapshot(
  id: string,
  payload: { asset_id: string; date: string; amount: number; source?: string },
): Promise<Snapshot> {
  return apiFetch<Snapshot>(`/api/snapshots/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteSnapshot(id: string): Promise<void> {
  await apiFetch<void>(`/api/snapshots/${id}`, { method: "DELETE" });
}
