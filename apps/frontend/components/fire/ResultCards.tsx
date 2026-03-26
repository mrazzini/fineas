import { KpiCard } from "@/components/ui/KpiCard";
import type { ProjectionResponse } from "@/lib/types";

interface ResultCardsProps {
  projection: ProjectionResponse;
}

export function ResultCards({ projection }: ResultCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <KpiCard
        label="FIRE Date"
        value={
          projection.fire_date
            ? new Date(projection.fire_date).toLocaleDateString("en-GB", {
                month: "short",
                year: "numeric",
              })
            : "Not Reached"
        }
        accentColor="bg-primary"
      />
      <KpiCard
        label="Remaining Months"
        value={
          projection.months_to_fire != null
            ? String(projection.months_to_fire)
            : "N/A"
        }
        accentColor="bg-[#64B5F6]"
      />
      <KpiCard
        label="Current Total"
        value={`€${parseFloat(projection.current_total).toLocaleString("en-GB", { minimumFractionDigits: 2 })}`}
        accentColor="bg-[#CE93D8]"
      />
    </div>
  );
}
