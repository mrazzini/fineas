import type {
  Asset,
  AssetCreate,
  AssetType,
  AssetUpdate,
  Snapshot,
  SnapshotCreate,
  ProjectionResponse,
  IngestRequest,
  IngestResponse,
  ApplyRequest,
  ApplyResponse,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export const login = (password: string) =>
  request<{ ok: boolean }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });

export const logout = () =>
  request<void>("/auth/logout", { method: "POST" });

export const getAuthStatus = () =>
  request<{ authenticated: boolean }>("/auth/status");

// ---------------------------------------------------------------------------
// Real-data loader (auth required)
// ---------------------------------------------------------------------------
export interface LoadSummary {
  assets_loaded: number;
  snapshots_loaded: number;
  skipped: string[];
}

export interface LoadAssetEntry {
  original_name: string;
  name: string;
  asset_type: AssetType;
  annualized_return_pct: string | null;
}

export interface LoadSnapshotEntry {
  asset_name: string;
  snapshot_date: string;
  balance: string;
}

export interface LoadPayload {
  assets: LoadAssetEntry[];
  snapshots: LoadSnapshotEntry[];
}

export const loadRealData = (payload: LoadPayload) =>
  request<LoadSummary>("/data/load", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export const getHealth = () => request<{ status: string }>("/health");

// ---------------------------------------------------------------------------
// Assets
// ---------------------------------------------------------------------------
export const getAssets = (includeArchived = false) =>
  request<Asset[]>(`/assets?include_archived=${includeArchived}`);

export const getAsset = (id: string) => request<Asset>(`/assets/${id}`);

export const createAsset = (data: AssetCreate) =>
  request<Asset>("/assets", { method: "POST", body: JSON.stringify(data) });

export const updateAsset = (id: string, data: AssetUpdate) =>
  request<Asset>(`/assets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteAsset = (id: string) =>
  request<void>(`/assets/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Snapshots
// ---------------------------------------------------------------------------
export const getSnapshots = (assetId: string) =>
  request<Snapshot[]>(`/assets/${assetId}/snapshots`);

export const createSnapshot = (assetId: string, data: SnapshotCreate) =>
  request<Snapshot>(`/assets/${assetId}/snapshots`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const upsertSnapshot = (assetId: string, data: SnapshotCreate) =>
  request<Snapshot>(`/assets/${assetId}/snapshots/upsert`, {
    method: "POST",
    body: JSON.stringify(data),
  });

// ---------------------------------------------------------------------------
// Portfolio / Projection
// ---------------------------------------------------------------------------
export const getProjection = (params?: {
  months?: number;
  monthly_contribution?: number;
  annual_expenses?: number;
  safe_withdrawal_rate?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.months != null)
    searchParams.set("months", String(params.months));
  if (params?.monthly_contribution != null)
    searchParams.set("monthly_contribution", String(params.monthly_contribution));
  if (params?.annual_expenses != null)
    searchParams.set("annual_expenses", String(params.annual_expenses));
  if (params?.safe_withdrawal_rate != null)
    searchParams.set("safe_withdrawal_rate", String(params.safe_withdrawal_rate));
  const qs = searchParams.toString();
  return request<ProjectionResponse>(`/portfolio/projection${qs ? `?${qs}` : ""}`);
};

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------
export const ingestText = (data: IngestRequest) =>
  request<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const applyIngest = (data: ApplyRequest) =>
  request<ApplyResponse>("/ingest/apply", {
    method: "POST",
    body: JSON.stringify(data),
  });
