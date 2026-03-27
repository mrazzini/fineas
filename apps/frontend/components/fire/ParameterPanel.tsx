"use client";

import { formatEUR } from "@/lib/format";

interface ParameterPanelProps {
  contribution: string;
  expenses: string;
  withdrawalRate: number;
  onContributionChange: (v: string) => void;
  onExpensesChange: (v: string) => void;
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
  const expensesNum = Number(expenses) || 0;

  return (
    <div className="glass-card rounded-xl p-8 space-y-8 lg:sticky lg:top-20 border-none shadow-2xl">
      <h2 className="text-xl font-headline font-bold flex items-center gap-2">
        Parameters
      </h2>

      <div>
        <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant mb-3">
          Monthly Contribution
        </label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 font-mono text-primary">
            €
          </span>
          <input
            type="text"
            inputMode="decimal"
            value={contribution}
            onChange={(e) => onContributionChange(e.target.value)}
            className="w-full bg-surface-container-highest border-none rounded-lg py-4 pl-10 pr-4 font-mono text-xl text-on-surface outline-none focus:ring-1 focus:ring-primary/30 transition-all"
          />
        </div>
      </div>

      <div>
        <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant mb-3">
          Annual Expenses
        </label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 font-mono text-primary">
            €
          </span>
          <input
            type="text"
            inputMode="decimal"
            value={expenses}
            onChange={(e) => onExpensesChange(e.target.value)}
            className="w-full bg-surface-container-highest border-none rounded-lg py-4 pl-10 pr-4 font-mono text-xl text-on-surface outline-none focus:ring-1 focus:ring-primary/30 transition-all"
          />
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant">
            Withdrawal Rate
          </label>
          <span className="font-mono text-primary text-sm font-bold">
            {(withdrawalRate * 100).toFixed(1)}%
          </span>
        </div>
        <input
          type="range"
          min="0.02"
          max="0.06"
          step="0.005"
          value={withdrawalRate}
          onChange={(e) => onWithdrawalRateChange(Number(e.target.value))}
          className="w-full accent-primary h-1.5 bg-surface-container-highest rounded-full appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-xs text-on-surface-variant font-label mt-1">
          <span>2%</span>
          <span>6%</span>
        </div>
      </div>

      <div>
        <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant mb-4">
          Projection Strategy
        </label>
        <div className="grid grid-cols-3 gap-2">
          <label className="cursor-pointer group">
            <input className="hidden peer" name="strategy" type="radio" />
            <div className="text-center py-3 rounded-lg bg-surface-container-low peer-checked:bg-primary/10 peer-checked:text-primary transition-all border border-transparent peer-checked:border-primary/30">
              <span className="text-xs font-label block">CONSERV</span>
            </div>
          </label>
          <label className="cursor-pointer group">
            <input
              className="hidden peer"
              name="strategy"
              type="radio"
              defaultChecked
            />
            <div className="text-center py-3 rounded-lg bg-surface-container-low peer-checked:bg-primary/10 peer-checked:text-primary transition-all border border-transparent peer-checked:border-primary/30">
              <span className="text-xs font-label block">BALANCED</span>
            </div>
          </label>
          <label className="cursor-pointer group">
            <input className="hidden peer" name="strategy" type="radio" />
            <div className="text-center py-3 rounded-lg bg-surface-container-low peer-checked:bg-primary/10 peer-checked:text-primary transition-all border border-transparent peer-checked:border-primary/30">
              <span className="text-xs font-label block">AGGRESS</span>
            </div>
          </label>
        </div>
      </div>

      <div className="pt-6 border-t border-outline-variant/10">
        <div className="flex justify-between items-end mb-4">
          <div>
            <span className="block font-label text-[10px] uppercase tracking-tighter text-on-surface-variant mb-1">
              Computed Target
            </span>
            <div className="bg-primary-container text-on-primary-container font-mono text-lg px-3 py-1 rounded-md font-bold">
              {formatEUR(fireTarget)}
            </div>
          </div>
        </div>
        <p className="text-xs text-on-surface-variant mt-0.5 mb-2">
          {expensesNum.toLocaleString()} / {(withdrawalRate * 100).toFixed(1)}%
        </p>
      </div>

      <button
        onClick={onRecalculate}
        className="w-full liquid-gradient text-on-primary font-headline font-bold py-4 rounded-lg shadow-lg shadow-primary/10 hover:brightness-110 active:scale-[0.98] transition-all"
      >
        Recalculate
      </button>
    </div>
  );
}
