"use client";

import { formatEUR } from "@/lib/format";

interface ParameterPanelProps {
  contribution: number;
  expenses: number;
  withdrawalRate: number;
  onContributionChange: (v: number) => void;
  onExpensesChange: (v: number) => void;
  onWithdrawalRateChange: (v: number) => void;
  onRecalculate: () => void;
  fireTarget: number;
}

export function ParameterPanel({
  contribution,
  expenses,
  withdrawalRate,
  onContributionChange,
  onExpensesChange,
  onWithdrawalRateChange,
  onRecalculate,
  fireTarget,
}: ParameterPanelProps) {
  return (
    <div className="bg-surface-container-low rounded-xl p-6 space-y-6 lg:sticky lg:top-20">
      <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider">
        Parameters
      </h2>

      <div>
        <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
          Monthly Contribution
        </label>
        <input
          type="number"
          value={contribution}
          onChange={(e) => onContributionChange(Number(e.target.value))}
          className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
          Annual Expenses
        </label>
        <input
          type="number"
          value={expenses}
          onChange={(e) => onExpensesChange(Number(e.target.value))}
          className="w-full bg-surface-container-highest rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <label className="block text-xs font-label text-on-surface-variant uppercase tracking-wider mb-1.5">
          Withdrawal Rate: {(withdrawalRate * 100).toFixed(1)}%
        </label>
        <input
          type="range"
          min="0.02"
          max="0.06"
          step="0.005"
          value={withdrawalRate}
          onChange={(e) => onWithdrawalRateChange(Number(e.target.value))}
          className="w-full accent-primary"
        />
        <div className="flex justify-between text-xs text-on-surface-variant font-label mt-1">
          <span>2%</span>
          <span>6%</span>
        </div>
      </div>

      <div className="bg-surface-container rounded-lg p-4">
        <p className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
          FIRE Target
        </p>
        <p className="text-xl font-mono font-bold text-primary mt-1">
          {formatEUR(fireTarget)}
        </p>
        <p className="text-xs text-on-surface-variant mt-0.5">
          {expenses.toLocaleString()} / {(withdrawalRate * 100).toFixed(1)}%
        </p>
      </div>

      <button
        onClick={onRecalculate}
        className="w-full px-4 py-2.5 rounded-lg text-sm font-medium liquid-gradient text-on-primary"
      >
        Recalculate
      </button>
    </div>
  );
}
