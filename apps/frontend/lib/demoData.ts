/**
 * Static demo fixture served to anonymous visitors.
 *
 * Lives entirely in the client bundle — the backend never reads it and never
 * serves it, so real owner data cannot leak through an unauth'd endpoint.
 * Authenticated visitors bypass this and fetch from the API.
 */
import type { Asset, Snapshot } from "./types";

const mkSnapshot = (
  asset_id: string,
  snapshot_date: string,
  balance: string,
  seq: number,
): Snapshot => ({
  id: `demo-snap-${asset_id}-${seq}`,
  asset_id,
  snapshot_date,
  balance,
  created_at: `${snapshot_date}T00:00:00Z`,
});

// UUIDs (not descriptive strings) — the stateless /projection/compute endpoint
// types asset_id as uuid.UUID and rejects anything else with 422.
const ID_CASH = "c821b972-3503-4222-87b4-02522e2b7f49";
const ID_WORLD_ETF = "81e2e0d1-481d-4c1f-8dab-db8c9426af55";
const ID_BONDS = "7b2397f4-cbcb-4d0f-a002-e3020a25c991";
const ID_CRYPTO = "87601c60-da65-46d1-b2d3-c9c2859169b3";
const ID_PENSION = "055b95df-e2d5-4b04-ad21-4f47a3cdd9d6";

export const DEMO_ASSETS: Asset[] = [
  {
    id: ID_CASH,
    name: "High-yield Savings",
    asset_type: "CASH",
    annualized_return_pct: "0.035",
    ticker: null,
    is_archived: false,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: ID_WORLD_ETF,
    name: "Global Equity ETF",
    asset_type: "STOCKS",
    annualized_return_pct: "0.085",
    ticker: "VWCE",
    is_archived: false,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: ID_BONDS,
    name: "Aggregate Bonds",
    asset_type: "BONDS",
    annualized_return_pct: "0.04",
    ticker: "AGGH",
    is_archived: false,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: ID_CRYPTO,
    name: "Bitcoin",
    asset_type: "CRYPTO",
    annualized_return_pct: "0.12",
    ticker: "BTC",
    is_archived: false,
    created_at: "2024-02-01T00:00:00Z",
  },
  {
    id: ID_PENSION,
    name: "Workplace Pension",
    asset_type: "PENSION_FUND",
    annualized_return_pct: "0.06",
    ticker: null,
    is_archived: false,
    created_at: "2024-01-01T00:00:00Z",
  },
];

const snapshotsFor = (
  id: string,
  monthly: Array<[string, string]>,
): Snapshot[] => monthly.map(([d, b], i) => mkSnapshot(id, d, b, i));

export const DEMO_SNAPSHOTS_BY_ASSET: Record<string, Snapshot[]> = {
  [ID_CASH]: snapshotsFor(ID_CASH, [
    ["2025-10-01", "12000.00"],
    ["2025-11-01", "12450.00"],
    ["2025-12-01", "12800.00"],
    ["2026-01-01", "13100.00"],
    ["2026-02-01", "13600.00"],
    ["2026-03-01", "14050.00"],
    ["2026-04-01", "14500.00"],
  ]),
  [ID_WORLD_ETF]: snapshotsFor(ID_WORLD_ETF, [
    ["2025-10-01", "48000.00"],
    ["2025-11-01", "49800.00"],
    ["2025-12-01", "51200.00"],
    ["2026-01-01", "52900.00"],
    ["2026-02-01", "54100.00"],
    ["2026-03-01", "55700.00"],
    ["2026-04-01", "57300.00"],
  ]),
  [ID_BONDS]: snapshotsFor(ID_BONDS, [
    ["2025-10-01", "15000.00"],
    ["2025-11-01", "15150.00"],
    ["2025-12-01", "15280.00"],
    ["2026-01-01", "15400.00"],
    ["2026-02-01", "15520.00"],
    ["2026-03-01", "15640.00"],
    ["2026-04-01", "15800.00"],
  ]),
  [ID_CRYPTO]: snapshotsFor(ID_CRYPTO, [
    ["2025-10-01", "6500.00"],
    ["2025-11-01", "7100.00"],
    ["2025-12-01", "6800.00"],
    ["2026-01-01", "7400.00"],
    ["2026-02-01", "7900.00"],
    ["2026-03-01", "8600.00"],
    ["2026-04-01", "9100.00"],
  ]),
  [ID_PENSION]: snapshotsFor(ID_PENSION, [
    ["2025-10-01", "22000.00"],
    ["2025-11-01", "22300.00"],
    ["2025-12-01", "22650.00"],
    ["2026-01-01", "23000.00"],
    ["2026-02-01", "23400.00"],
    ["2026-03-01", "23800.00"],
    ["2026-04-01", "24300.00"],
  ]),
};
