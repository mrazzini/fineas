"use client";

import {
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { formatEUR } from "@/lib/format";

interface AreaChartProps {
  data: { label: string; value: number }[];
  referenceLine?: { value: number; label: string };
  height?: number;
  color?: string;
}

export function AreaChart({
  data,
  referenceLine,
  height = 300,
  color = "#3fff8b",
}: AreaChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsAreaChart
        data={data}
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
      >
        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="#232629"
          vertical={false}
        />
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
          labelStyle={{ color: "#aaabad", fontFamily: "Space Grotesk" }}
          formatter={(value: number) => [formatEUR(value), "Balance"]}
        />
        {referenceLine && (
          <ReferenceLine
            y={referenceLine.value}
            stroke="#ff716c"
            strokeDasharray="6 4"
            label={{
              value: referenceLine.label,
              position: "right",
              fill: "#ff716c",
              fontSize: 11,
              fontFamily: "Space Grotesk",
            }}
          />
        )}
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill="url(#areaGradient)"
        />
      </RechartsAreaChart>
    </ResponsiveContainer>
  );
}
