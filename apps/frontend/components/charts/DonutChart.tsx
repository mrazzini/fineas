"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { formatEUR } from "@/lib/format";

interface DonutChartProps {
  data: { name: string; value: number; color: string }[];
  centerLabel?: string;
  centerValue?: string;
  height?: number;
}

export function DonutChart({
  data,
  centerLabel,
  centerValue,
  height = 240,
}: DonutChartProps) {
  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            innerRadius="65%"
            outerRadius="85%"
            paddingAngle={2}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      {(centerLabel || centerValue) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {centerLabel && (
            <span className="text-xs font-label text-on-surface-variant">
              {centerLabel}
            </span>
          )}
          {centerValue && (
            <span className="text-lg font-mono font-bold text-on-surface">
              {centerValue}
            </span>
          )}
        </div>
      )}
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 justify-center">
        {data.map((entry) => (
          <div key={entry.name} className="flex items-center gap-1.5 text-xs">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-on-surface-variant font-label">
              {entry.name}
            </span>
            <span className="font-mono text-on-surface">
              {formatEUR(entry.value, true)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
