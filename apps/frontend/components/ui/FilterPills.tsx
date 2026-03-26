"use client";

interface FilterPillsProps {
  options: { value: string; label: string }[];
  selected: string;
  onChange: (value: string) => void;
}

export function FilterPills({ options, selected, onChange }: FilterPillsProps) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1">
      {options.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => onChange(value)}
          className={`px-3 py-1.5 rounded-full text-xs font-label whitespace-nowrap transition-colors ${
            selected === value
              ? "bg-primary/10 text-primary"
              : "bg-surface-container-high text-on-surface-variant hover:text-on-surface"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
