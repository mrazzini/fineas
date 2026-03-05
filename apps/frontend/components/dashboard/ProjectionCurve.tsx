"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CompoundResult } from "@/types/schema";
import { runProjection } from "@/lib/api";

interface Props {
  monthlyContribution?: number;
  targetAmount?: number;
}

const formatEUR = (v: number) =>
  new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

export function ProjectionCurve({ monthlyContribution = 750, targetAmount = 500000 }: Props) {
  const [result, setResult] = useState<CompoundResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    runProjection({ monthly_contribution: monthlyContribution, horizon_years: 20, target_amount: targetAmount })
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setLoading(false));
  }, [monthlyContribution, targetAmount]);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
        Loading projection…
      </div>
    );
  }

  if (!result) {
    return (
      <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
        Could not load projection. Is the API running?
      </div>
    );
  }

  const data = result.yearly_trajectory.map((p) => ({
    year: p.year,
    value: p.projected_value,
    contributions: p.cumulative_contributions,
  }));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>Weighted return: {(result.weighted_return * 100).toFixed(2)}% real</span>
        {result.target_hit_year && (
          <span className="text-emerald-600 font-medium">
            FIRE target reached: {result.target_hit_year}
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="projGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="year" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis
            tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={56}
          />
          <Tooltip
            formatter={(value: number | undefined, name: string | undefined) => [
              formatEUR(value ?? 0),
              name === "value" ? "Projected" : "Contributions",
            ]}
            contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13 }}
          />
          {targetAmount && (
            <ReferenceLine
              y={targetAmount}
              stroke="#f59e0b"
              strokeDasharray="6 3"
              label={{ value: "FIRE", position: "right", fontSize: 11, fill: "#f59e0b" }}
            />
          )}
          <Area
            type="monotone"
            dataKey="value"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#projGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
