import type {
  CompoundResult,
  NetWorthHistory,
  PortfolioSummary,
} from "@/types/schema";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
