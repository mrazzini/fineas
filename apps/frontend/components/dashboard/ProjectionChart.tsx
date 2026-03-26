"use client";

import { useState } from "react";
import { AreaChart } from "@/components/charts/AreaChart";
import { FilterPills } from "@/components/ui/FilterPills";
import type { MonthlySlice } from "@/lib/types";

const RANGE_OPTIONS = [
  { value: "120", label: "10Y" },
  { value: "300", label: "25Y" },
  { value: "all", label: "MAX" },
];

interface ProjectionChartProps {
  monthly: MonthlySlice[];
  fireTarget: number | null;
}

export function ProjectionChart({ monthly, fireTarget }: ProjectionChartProps) {
  const [range, setRange] = useState("120");

  const slices =
    range === "all" ? monthly : monthly.slice(0, parseInt(range));

  const data = slices.map((s) => ({
    label: new Date(s.date).toLocaleDateString("en-GB", {
      month: "short",
      year: "2-digit",
    }),
    value: parseFloat(s.portfolio_total),
  }));

  return (
    <div className="bg-surface-container-low rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider">
          Portfolio Projection
        </h2>
        <FilterPills
          options={RANGE_OPTIONS}
          selected={range}
          onChange={setRange}
        />
      </div>
      <AreaChart
        data={data}
        height={320}
        referenceLine={
          fireTarget
            ? { value: fireTarget, label: "FIRE Target" }
            : undefined
        }
      />
    </div>
  );
}
