export const ASSET_TYPE_LABELS: Record<string, string> = {
  cash: "Cash",
  stocks: "Stocks",
  bonds: "Bonds",
  p2p_lending: "P2P Lending",
  pension: "Pension",
  money_market: "Money Market",
};

export const ASSET_TYPE_COLORS: Record<string, string> = {
  cash: "#94a3b8",
  stocks: "#3b82f6",
  bonds: "#8b5cf6",
  p2p_lending: "#f59e0b",
  pension: "#10b981",
  money_market: "#06b6d4",
};

export const EUR = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export const EUR_PRECISE = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const PCT = new Intl.NumberFormat("it-IT", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
