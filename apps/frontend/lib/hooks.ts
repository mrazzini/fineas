/**
 * Auth-branching data hooks.
 *
 * Anonymous visitors see demo fixtures for read-views and hit the stateless
 * compute endpoints with fixture data. The authenticated owner fetches from
 * the DB-backed API. Both paths share the same compute endpoints.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  computeProjection,
  getAssets,
  getAuthStatus,
  getSnapshots,
} from "./api";
import {
  DEMO_ASSETS,
  DEMO_SNAPSHOTS_BY_ASSET,
} from "./demoData";
import type {
  Asset,
  ProjectionRequest,
  ProjectionResponse,
  Snapshot,
} from "./types";

export function useAuthStatus() {
  return useQuery({
    queryKey: ["auth-status"],
    queryFn: getAuthStatus,
    staleTime: 60_000,
  });
}

export function useIsOwner(): boolean {
  const { data } = useAuthStatus();
  return data?.authenticated ?? false;
}

export function useAssets() {
  const isOwner = useIsOwner();
  const authQuery = useAuthStatus();
  return useQuery({
    queryKey: ["assets", isOwner],
    enabled: !authQuery.isLoading,
    queryFn: async (): Promise<Asset[]> => {
      if (isOwner) return getAssets();
      return DEMO_ASSETS;
    },
  });
}

export function useAsset(id: string) {
  const isOwner = useIsOwner();
  const authQuery = useAuthStatus();
  return useQuery({
    queryKey: ["asset", isOwner, id],
    enabled: !authQuery.isLoading && !!id,
    queryFn: async (): Promise<Asset | null> => {
      if (isOwner) {
        const assets = await getAssets();
        return assets.find((a) => a.id === id) ?? null;
      }
      return DEMO_ASSETS.find((a) => a.id === id) ?? null;
    },
  });
}

export function useSnapshots(assetId: string) {
  const isOwner = useIsOwner();
  const authQuery = useAuthStatus();
  return useQuery({
    queryKey: ["snapshots", isOwner, assetId],
    enabled: !authQuery.isLoading && !!assetId,
    queryFn: async (): Promise<Snapshot[]> => {
      if (isOwner) return getSnapshots(assetId);
      return DEMO_SNAPSHOTS_BY_ASSET[assetId] ?? [];
    },
  });
}

export function useLatestBalances(assets: Asset[]) {
  const isOwner = useIsOwner();
  const authQuery = useAuthStatus();
  return useQuery({
    queryKey: ["latestBalances", isOwner, assets.map((a) => a.id)],
    enabled: !authQuery.isLoading && assets.length > 0,
    queryFn: async (): Promise<Record<string, Snapshot | null>> => {
      if (isOwner) {
        const entries = await Promise.all(
          assets.map(async (a) => {
            const snaps = await getSnapshots(a.id);
            const latest = snaps.length > 0 ? snaps[snaps.length - 1] : null;
            return [a.id, latest] as [string, Snapshot | null];
          }),
        );
        return Object.fromEntries(entries);
      }
      const entries = assets.map((a) => {
        const snaps = DEMO_SNAPSHOTS_BY_ASSET[a.id] ?? [];
        const latest = snaps.length > 0 ? snaps[snaps.length - 1] : null;
        return [a.id, latest] as [string, Snapshot | null];
      });
      return Object.fromEntries(entries);
    },
  });
}

interface ProjectionParams {
  months?: number;
  monthly_contribution?: number | string;
  annual_expenses?: number | string | null;
  safe_withdrawal_rate?: number;
}

/**
 * Compute a FIRE projection given the current assets + their latest balances.
 * Always calls the stateless /projection/compute endpoint — works for anon
 * (fixture data) and authed (real data) callers alike.
 */
export function useProjection(
  assets: Asset[],
  latestBalances: Record<string, Snapshot | null>,
  params: ProjectionParams,
  extraKey: unknown = null,
) {
  // The queryFn reads per-asset balances, so the key must include them —
  // otherwise the first render (with an empty balances map) caches a
  // zeroed-out result that never refreshes when the balances resolve.
  const balanceFingerprint = assets.map(
    (a) => `${a.id}:${latestBalances[a.id]?.balance ?? ""}`,
  );
  const ready =
    assets.length > 0 &&
    assets.every((a) => latestBalances[a.id] !== undefined);
  return useQuery<ProjectionResponse>({
    queryKey: ["projection", balanceFingerprint, params, extraKey],
    enabled: ready,
    queryFn: () => {
      const req: ProjectionRequest = {
        assets: assets.map((a) => ({
          asset_id: a.id,
          name: a.name,
          current_balance: latestBalances[a.id]?.balance ?? "0",
          annualized_return_pct: a.annualized_return_pct ?? "0",
        })),
        months: params.months,
        monthly_contribution:
          params.monthly_contribution != null
            ? String(params.monthly_contribution)
            : undefined,
        annual_expenses:
          params.annual_expenses != null
            ? String(params.annual_expenses)
            : undefined,
        safe_withdrawal_rate: params.safe_withdrawal_rate,
      };
      return computeProjection(req);
    },
  });
}
