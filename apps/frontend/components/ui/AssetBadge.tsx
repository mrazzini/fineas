import type { AssetType } from "@/lib/types";
import { ASSET_TYPE_COLORS, ASSET_TYPE_LABELS } from "@/lib/constants";

interface AssetBadgeProps {
  type: AssetType;
}

export function AssetBadge({ type }: AssetBadgeProps) {
  const colors = ASSET_TYPE_COLORS[type];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-label ${colors.bg} ${colors.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
      {ASSET_TYPE_LABELS[type]}
    </span>
  );
}
