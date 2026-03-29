export type AssetType =
  | "CASH"
  | "STOCKS"
  | "BONDS"
  | "REAL_ESTATE"
  | "CRYPTO"
  | "PENSION_FUND"
  | "OTHER";

export interface Asset {
  id: string;
  name: string;
  asset_type: AssetType;
  annualized_return_pct: string | null;
  ticker: string | null;
  is_archived: boolean;
  created_at: string;
}

export interface AssetCreate {
  name: string;
  asset_type: AssetType;
  annualized_return_pct?: string | null;
  ticker?: string | null;
}

export interface AssetUpdate {
  name?: string | null;
  asset_type?: AssetType | null;
  annualized_return_pct?: string | null;
  ticker?: string | null;
  is_archived?: boolean | null;
}

export interface Snapshot {
  id: string;
  asset_id: string;
  snapshot_date: string;
  balance: string;
  created_at: string;
}

export interface SnapshotCreate {
  snapshot_date: string;
  balance: string;
}

export interface AssetProjection {
  asset_id: string;
  name: string;
  current_balance: string;
  projected_balance: string;
}

export interface MonthlySlice {
  month: number;
  date: string;
  portfolio_total: string;
  asset_balances: Record<string, string>;
}

export interface ProjectionResponse {
  current_total: string;
  fire_target: string | null;
  fire_date: string | null;
  months_to_fire: number | null;
  asset_summaries: AssetProjection[];
  monthly: MonthlySlice[];
}

export interface IngestRequest {
  text: string;
}

export interface AmbiguousAsset {
  asset_index: number;
  original_name: string;
  candidates: string[];
}

export interface IngestResponse {
  parsed_assets: Record<string, unknown>[];
  parsed_snapshots: Record<string, unknown>[];
  validated_assets: Record<string, unknown>[];
  validated_snapshots: Record<string, unknown>[];
  validation_errors: string[];
  is_valid: boolean;
  ambiguous_assets: AmbiguousAsset[];
}

export interface ApplyRequest {
  validated_assets: Record<string, unknown>[];
  validated_snapshots: Record<string, unknown>[];
  resolved_names: Record<string, string>;
}

export interface ApplyResponse {
  applied_assets: Record<string, unknown>[];
  applied_snapshots: Record<string, unknown>[];
  apply_errors: string[];
  success: boolean;
}
