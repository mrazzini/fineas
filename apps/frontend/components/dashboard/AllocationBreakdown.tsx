"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { HoldingInfo } from "@/types/schema";

const COLORS: Record<string, string> = {
  cash: "#94a3b8",
  stocks: "#3b82f6",
  bonds: "#8b5cf6",
  p2p_lending: "#f59e0b",
  pension: "#10b981",
  money_market: "#06b6d4",
};

const TYPE_LABELS: Record<string, string> = {
  cash: "Cash",
  stocks: "Stocks",
  bonds: "Bonds",
  p2p_lending: "P2P Lending",
  pension: "Pension",
  money_market: "Money Market",
};

interface Props {
  holdings: HoldingInfo[];
  total: number;
}

export function AllocationBreakdown({ holdings, total }: Props) {
  // Aggregate by asset_type for the pie
  const byType = holdings.reduce<Record<string, number>>((acc, h) => {
    acc[h.asset_type] = (acc[h.asset_type] ?? 0) + h.current_amount;
    return acc;
  }, {});

  const pieData = Object.entries(byType).map(([type, value]) => ({
    name: TYPE_LABELS[type] ?? type,
    value,
    type,
    pct: total ? ((value / total) * 100).toFixed(1) : "0",
  }));

  const formatEUR = (v: number) =>
    new Intl.NumberFormat("it-IT", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 0,
    }).format(v);

  return (
    <div className="flex items-center gap-6">
      <div className="shrink-0">
        <ResponsiveContainer width={180} height={180}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius={52}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
            >
              {pieData.map((entry) => (
                <Cell key={entry.type} fill={COLORS[entry.type] ?? "#64748b"} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number | undefined) => [formatEUR(value ?? 0)]}
              contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-col gap-1.5 text-sm">
        {pieData.map((entry) => (
          <div key={entry.type} className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
              style={{ background: COLORS[entry.type] ?? "#64748b" }}
            />
            <span className="text-muted-foreground">{entry.name}</span>
            <span className="ml-auto font-medium tabular-nums">{entry.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
