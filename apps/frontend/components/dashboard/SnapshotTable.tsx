import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { HoldingInfo } from "@/types/schema";

const TYPE_LABELS: Record<string, string> = {
  cash: "Cash",
  stocks: "Stocks",
  bonds: "Bonds",
  p2p_lending: "P2P",
  pension: "Pension",
  money_market: "Money Mkt",
};

const formatEUR = (v: number) =>
  new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
  }).format(v);

const formatPct = (v: number) =>
  `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;

interface Props {
  holdings: HoldingInfo[];
}

export function SnapshotTable({ holdings }: Props) {
  const sorted = [...holdings].sort((a, b) => b.current_amount - a.current_amount);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Asset</TableHead>
          <TableHead>Type</TableHead>
          <TableHead className="text-right">Value</TableHead>
          <TableHead className="text-right">Alloc %</TableHead>
          <TableHead className="text-right">Change</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((h) => (
          <TableRow key={h.asset_id}>
            <TableCell className="font-medium">{h.asset_name}</TableCell>
            <TableCell>
              <Badge variant="outline" className="text-xs">
                {TYPE_LABELS[h.asset_type] ?? h.asset_type}
              </Badge>
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatEUR(h.current_amount)}
            </TableCell>
            <TableCell className="text-right tabular-nums text-muted-foreground">
              {h.allocation_pct.toFixed(1)}%
            </TableCell>
            <TableCell
              className={`text-right tabular-nums text-sm ${
                h.change_since_last >= 0 ? "text-emerald-600" : "text-red-500"
              }`}
            >
              {formatPct(h.change_pct)}
              <span className="ml-1 text-xs text-muted-foreground">
                ({formatEUR(h.change_since_last)})
              </span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
