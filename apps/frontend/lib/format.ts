const eurFormatter = new Intl.NumberFormat("en-EU", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactFormatter = new Intl.NumberFormat("en-EU", {
  style: "currency",
  currency: "EUR",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatEUR(value: string | number, compact = false): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "€0.00";
  return compact ? compactFormatter.format(num) : eurFormatter.format(num);
}

export function formatPercent(value: string | number, decimals = 2): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0%";
  return `${(num * 100).toFixed(decimals)}%`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
