// Shared TypeScript types — derived from Pydantic models (source of truth: backend)
// Keep in sync manually for v1. Types match apps/api/app/schemas/*.py

export type AssetType =
  | "cash"
  | "stocks"
  | "bonds"
  | "p2p_lending"
  | "pension"
  | "money_market";

export type SnapshotSource = "manual" | "nl_agent" | "csv_import" | "pdf_import" | "excel_migration";

export interface Asset {
  id: string;
  name: string;
  asset_type: AssetType;
  platform: string | null;
  expected_annual_return: number | null;
  is_active: boolean;
  metadata_: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Snapshot {
  id: string;
  asset_id: string;
  date: string; // ISO date "YYYY-MM-DD"
  amount: number;
  source: SnapshotSource;
  created_at: string;
}

export interface HoldingInfo {
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  platform: string | null;
  current_amount: number;
  snapshot_date: string;
  allocation_pct: number;
  change_since_last: number;
  change_pct: number;
}

export interface PortfolioSummary {
  total_net_worth: number;
  holdings: HoldingInfo[];
  as_of_date: string;
}

export interface NetWorthHistory {
  date: string;
  total: number;
}

export interface Goal {
  id: string;
  name: string;
  description: string | null;
  target_amount: number;
  target_date: string | null;
  goal_type: "fire" | "milestone" | "emergency_fund" | "purchase";
  asset_scope: string | string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CompoundYearlyPoint {
  year: number;
  projected_value: number;
  cumulative_contributions: number;
  cumulative_returns: number;
}

export interface CompoundResult {
  yearly_trajectory: CompoundYearlyPoint[];
  target_hit_year: number | null;
  final_value_at_horizon: number;
  weighted_return: number;
}

export interface MonteCarloResult {
  simulations: number;
  target_hit_probability: number;
  median_years_to_target: number;
  percentiles: Record<string, { years: number; final_value: number }>;
  yearly_trajectory: Array<{
    year: number;
    p10: number;
    p25: number;
    p50: number;
    p75: number;
    p90: number;
  }>;
}

// WebSocket protocol
export interface ChatMessage {
  type: "user_message" | "confirmation_response";
  content?: string;
  confirmed?: boolean;
  edits?: Record<string, number>;
}

export interface AgentResponse {
  type: "thinking" | "response" | "confirmation_request" | "update_complete" | "error";
  content: string;
  data?: {
    updates?: AssetUpdate[];
    net_worth?: number;
    projection?: CompoundResult;
  };
}

export interface AssetUpdate {
  asset_name: string;
  old_amount: number;
  new_amount: number;
  delta: number;
  delta_pct: number;
  is_anomaly: boolean;
  anomaly_reason?: string;
}
