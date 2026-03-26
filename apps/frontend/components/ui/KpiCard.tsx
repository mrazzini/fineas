interface KpiCardProps {
  label: string;
  value: string;
  accentColor?: string;
  subtitle?: string;
}

export function KpiCard({
  label,
  value,
  accentColor = "bg-primary",
  subtitle,
}: KpiCardProps) {
  return (
    <div className="bg-surface-container-low rounded-xl p-4 flex gap-3">
      <div className={`w-1 rounded-full ${accentColor} shrink-0`} />
      <div className="min-w-0">
        <p className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
          {label}
        </p>
        <p className="text-xl font-mono font-bold text-on-surface mt-1 truncate">
          {value}
        </p>
        {subtitle && (
          <p className="text-xs font-label text-on-surface-variant mt-0.5">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
