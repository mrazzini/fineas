"use client";

import { DataTable } from "@/components/ui/DataTable";
import { formatEUR, formatDate } from "@/lib/format";
import type { MonthlySlice } from "@/lib/types";

interface BreakdownTableProps {
  monthly: MonthlySlice[];
  fireMonth: number | null;
}

export function BreakdownTable({ monthly, fireMonth }: BreakdownTableProps) {
  // Sample: show every 12th month + the FIRE month
  const sampled = monthly.filter(
    (s) => s.month % 12 === 0 || s.month === fireMonth
  );

  const columns = [
    {
      key: "month",
      header: "Month",
      render: (s: MonthlySlice) => (
        <span
          className={
            s.month === fireMonth
              ? "text-primary font-bold"
              : "text-on-surface-variant"
          }
        >
          {s.month}
        </span>
      ),
    },
    {
      key: "date",
      header: "Date",
      render: (s: MonthlySlice) => (
        <span
          className={s.month === fireMonth ? "text-primary font-bold" : ""}
        >
          {formatDate(s.date)}
        </span>
      ),
    },
    {
      key: "total",
      header: "Portfolio Total",
      align: "right" as const,
      mono: true,
      render: (s: MonthlySlice) => (
        <span
          className={s.month === fireMonth ? "text-primary font-bold" : ""}
        >
          {formatEUR(s.portfolio_total)}
        </span>
      ),
    },
  ];

  return (
    <div className="bg-surface-container-low rounded-xl overflow-hidden">
      <div className="px-6 pt-6 pb-2">
        <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider">
          Annual Breakdown
        </h2>
      </div>
      <DataTable
        columns={columns}
        data={sampled}
        keyExtractor={(s) => String(s.month)}
      />
    </div>
  );
}
