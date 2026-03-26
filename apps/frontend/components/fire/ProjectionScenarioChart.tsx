"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import { formatEUR } from "@/lib/format";
import type { ProjectionResponse } from "@/lib/types";

interface ProjectionScenarioChartProps {
  conservative: ProjectionResponse | null;
  balanced: ProjectionResponse | null;
  aggressive: ProjectionResponse | null;
  fireTarget: number;
}

export function ProjectionScenarioChart({
  conservative,
  balanced,
  aggressive,
  fireTarget,
}: ProjectionScenarioChartProps) {
  const maxLen = Math.max(
    conservative?.monthly.length ?? 0,
    balanced?.monthly.length ?? 0,
    aggressive?.monthly.length ?? 0
  );

  const data = Array.from({ length: maxLen }, (_, i) => ({
    label:
      balanced?.monthly[i]
        ? new Date(balanced.monthly[i].date).toLocaleDateString("en-GB", {
            month: "short",
            year: "2-digit",
          })
        : `M${i + 1}`,
    conservative: conservative?.monthly[i]
      ? parseFloat(conservative.monthly[i].portfolio_total)
      : undefined,
    balanced: balanced?.monthly[i]
      ? parseFloat(balanced.monthly[i].portfolio_total)
      : undefined,
    aggressive: aggressive?.monthly[i]
      ? parseFloat(aggressive.monthly[i].portfolio_total)
      : undefined,
  }));

  return (
    <div className="bg-surface-container-low rounded-xl p-6">
      <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider mb-4">
        Scenario Projections
      </h2>
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#232629" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "#aaabad", fontSize: 11, fontFamily: "Space Grotesk" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#aaabad", fontSize: 11, fontFamily: "JetBrains Mono" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => formatEUR(v, true)}
            width={70}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(23,26,28,0.9)",
              border: "1px solid rgba(70,72,74,0.15)",
              borderRadius: "12px",
              backdropFilter: "blur(24px)",
              fontFamily: "JetBrains Mono",
              fontSize: "13px",
            }}
            formatter={(value: number, name: string) => [
              formatEUR(value),
              name.charAt(0).toUpperCase() + name.slice(1),
            ]}
          />
          <Legend
            wrapperStyle={{ fontFamily: "Space Grotesk", fontSize: "12px" }}
          />
          <ReferenceLine
            y={fireTarget}
            stroke="#ff716c"
            strokeDasharray="6 4"
            label={{
              value: "FIRE Target",
              position: "right",
              fill: "#ff716c",
              fontSize: 11,
            }}
          />
          <Line
            type="monotone"
            dataKey="conservative"
            stroke="#64B5F6"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="balanced"
            stroke="#3fff8b"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="aggressive"
            stroke="#CE93D8"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
