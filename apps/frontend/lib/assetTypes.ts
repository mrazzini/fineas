import type { AssetType } from "./types";

export const CANONICAL_ASSET_TYPES: AssetType[] = [
  "CASH",
  "STOCKS",
  "BONDS",
  "REAL_ESTATE",
  "CRYPTO",
  "PENSION_FUND",
  "OTHER",
];

const ALIASES: Record<string, AssetType> = {
  cash: "CASH",
  stocks: "STOCKS",
  stock: "STOCKS",
  equities: "STOCKS",
  equity: "STOCKS",
  bonds: "BONDS",
  bond: "BONDS",
  realestate: "REAL_ESTATE",
  real_estate: "REAL_ESTATE",
  crypto: "CRYPTO",
  cryptocurrency: "CRYPTO",
  pension: "PENSION_FUND",
  pensionfund: "PENSION_FUND",
  pension_fund: "PENSION_FUND",
  retirement: "PENSION_FUND",
  retirementfund: "PENSION_FUND",
  p2p: "OTHER",
  p2plending: "OTHER",
  other: "OTHER",
};

const normalize = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9_]/g, "");

export function suggestAssetType(raw: string): AssetType {
  return ALIASES[normalize(raw)] ?? "OTHER";
}
