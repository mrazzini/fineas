"use client";

import { useState } from "react";
import { useAssets, useLatestBalances, useProjection } from "@/lib/hooks";
import { ParameterPanel } from "@/components/fire/ParameterPanel";
import { ResultCards } from "@/components/fire/ResultCards";
import { ProjectionScenarioChart } from "@/components/fire/ProjectionScenarioChart";
import { BreakdownTable } from "@/components/fire/BreakdownTable";

export default function FireCalculatorPage() {
  const [contribution, setContribution] = useState("1200");
  const [expenses, setExpenses] = useState("30000");
  const [withdrawalRate, setWithdrawalRate] = useState(0.04);
  const [queryParams, setQueryParams] = useState({
    contribution: 1200,
    expenses: 30000,
    withdrawalRate: 0.04,
  });

  const fireTarget = queryParams.expenses / queryParams.withdrawalRate;

  const { data: assets = [] } = useAssets();
  const { data: latestBalances = {} } = useLatestBalances(assets);

  const { data: balanced } = useProjection(
    assets,
    latestBalances,
    {
      months: 300,
      monthly_contribution: queryParams.contribution,
      annual_expenses: queryParams.expenses,
      safe_withdrawal_rate: queryParams.withdrawalRate,
    },
    "balanced",
  );

  const { data: conservative } = useProjection(
    assets,
    latestBalances,
    {
      months: 300,
      monthly_contribution: queryParams.contribution,
      annual_expenses: queryParams.expenses,
      safe_withdrawal_rate: Math.min(queryParams.withdrawalRate + 0.01, 0.06),
    },
    "conservative",
  );

  const { data: aggressive } = useProjection(
    assets,
    latestBalances,
    {
      months: 300,
      monthly_contribution: queryParams.contribution,
      annual_expenses: queryParams.expenses,
      safe_withdrawal_rate: Math.max(queryParams.withdrawalRate - 0.01, 0.02),
    },
    "aggressive",
  );

  const handleRecalculate = () => {
    setQueryParams({
      contribution: Number(contribution) || 0,
      expenses: Number(expenses) || 0,
      withdrawalRate,
    });
  };

  return (
    <div className="py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-headline font-bold tracking-tight">
          FIRE Calculator
        </h1>
        <p className="text-sm text-on-surface-variant mt-1">
          Project your path to financial independence
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <ParameterPanel
            contribution={contribution}
            expenses={expenses}
            withdrawalRate={withdrawalRate}
            onContributionChange={setContribution}
            onExpensesChange={setExpenses}
            onWithdrawalRateChange={setWithdrawalRate}
            onRecalculate={handleRecalculate}
            fireTarget={fireTarget}
          />
        </div>

        <div className="lg:col-span-3 space-y-6">
          {balanced ? (
            <>
              <ResultCards projection={balanced} />
              <ProjectionScenarioChart
                conservative={conservative ?? null}
                balanced={balanced}
                aggressive={aggressive ?? null}
                fireTarget={fireTarget}
              />
              <BreakdownTable
                monthly={balanced.monthly}
                fireMonth={balanced.months_to_fire}
              />
            </>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
