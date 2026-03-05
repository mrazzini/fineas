"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { AssetUpdate } from "@/types/schema";

interface Props {
  updates: AssetUpdate[];
  onConfirm: (edits?: Record<string, number>) => void;
  onCancel: () => void;
}

const formatEUR = (v: number) =>
  new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
  }).format(v);

export function ConfirmationCard({ updates, onConfirm, onCancel }: Props) {
  const [editing, setEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, number>>(
    Object.fromEntries(updates.map((u) => [u.asset_name, u.new_amount]))
  );

  const handleConfirm = () => {
    if (editing) {
      onConfirm(editValues);
    } else {
      onConfirm();
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden text-sm">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <span className="font-medium text-slate-700">Review Updates</span>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-blue-600 hover:underline"
          >
            Edit values
          </button>
        )}
      </div>

      <table className="w-full">
        <thead>
          <tr className="text-xs text-slate-500 border-b border-slate-100">
            <th className="text-left px-4 py-2 font-medium">Asset</th>
            <th className="text-right px-4 py-2 font-medium">Before</th>
            <th className="text-right px-4 py-2 font-medium">After</th>
            <th className="text-right px-4 py-2 font-medium">Change</th>
          </tr>
        </thead>
        <tbody>
          {updates.map((u) => (
            <tr
              key={u.asset_name}
              className={`border-b border-slate-50 last:border-0 ${
                u.is_anomaly ? "bg-amber-50" : ""
              }`}
            >
              <td className="px-4 py-2.5">
                <span className="font-medium text-slate-800">{u.asset_name}</span>
                {u.is_anomaly && (
                  <Badge variant="outline" className="ml-2 text-xs border-amber-400 text-amber-700">
                    ⚠ {u.anomaly_reason}
                  </Badge>
                )}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">
                {formatEUR(u.old_amount)}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums">
                {editing ? (
                  <input
                    type="number"
                    value={editValues[u.asset_name] ?? u.new_amount}
                    onChange={(e) =>
                      setEditValues((prev) => ({
                        ...prev,
                        [u.asset_name]: parseFloat(e.target.value) || 0,
                      }))
                    }
                    className="w-28 text-right border border-slate-300 rounded px-2 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <span className="font-medium text-slate-800">
                    {formatEUR(u.new_amount)}
                  </span>
                )}
              </td>
              <td
                className={`px-4 py-2.5 text-right tabular-nums text-xs font-medium ${
                  u.delta >= 0 ? "text-emerald-600" : "text-red-500"
                }`}
              >
                {u.delta >= 0 ? "+" : ""}
                {u.delta_pct.toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="px-4 py-3 flex gap-2 justify-end bg-slate-50 border-t border-slate-100">
        <button
          onClick={onCancel}
          className="px-4 py-1.5 text-sm text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          className="px-4 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium"
        >
          {editing ? "Confirm with edits" : "Confirm"}
        </button>
      </div>
    </div>
  );
}
