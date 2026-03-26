import type { AssetType } from "./types";

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  CASH: "Cash",
  STOCKS: "Stocks",
  BONDS: "Bonds",
  REAL_ESTATE: "Real Estate",
  CRYPTO: "Crypto",
  PENSION_FUND: "Pension",
  OTHER: "Other",
};

/**
 * Design system badge colors per asset type.
 * - bg: 10% opacity background
 * - text: full-opacity text
 * - dot: full-opacity dot indicator
 * - chart: recharts fill color
 */
export const ASSET_TYPE_COLORS: Record<
  AssetType,
  { bg: string; text: string; dot: string; chart: string }
> = {
  CASH: {
    bg: "bg-[#FFB74D]/10",
    text: "text-[#FFB74D]",
    dot: "bg-[#FFB74D]",
    chart: "#FFB74D",
  },
  STOCKS: {
    bg: "bg-primary/10",
    text: "text-primary",
    dot: "bg-primary",
    chart: "#3fff8b",
  },
  BONDS: {
    bg: "bg-[#64B5F6]/10",
    text: "text-[#64B5F6]",
    dot: "bg-[#64B5F6]",
    chart: "#64B5F6",
  },
  REAL_ESTATE: {
    bg: "bg-[#4DB6AC]/10",
    text: "text-[#4DB6AC]",
    dot: "bg-[#4DB6AC]",
    chart: "#4DB6AC",
  },
  CRYPTO: {
    bg: "bg-[#CE93D8]/10",
    text: "text-[#CE93D8]",
    dot: "bg-[#CE93D8]",
    chart: "#CE93D8",
  },
  PENSION_FUND: {
    bg: "bg-[#7986CB]/10",
    text: "text-[#7986CB]",
    dot: "bg-[#7986CB]",
    chart: "#7986CB",
  },
  OTHER: {
    bg: "bg-on-surface-variant/10",
    text: "text-on-surface-variant",
    dot: "bg-on-surface-variant",
    chart: "#aaabad",
  },
};

export const ALL_ASSET_TYPES: AssetType[] = [
  "STOCKS",
  "BONDS",
  "CASH",
  "CRYPTO",
  "REAL_ESTATE",
  "PENSION_FUND",
  "OTHER",
];
