"use client";

interface InputPanelProps {
  text: string;
  onTextChange: (v: string) => void;
  onParse: () => void;
  isParsing: boolean;
}

const FORMAT_HINTS = [
  "Free text",
  "CSV",
  "Tab-separated",
  "Spreadsheet paste",
];

export function InputPanel({ text, onTextChange, onParse, isParsing }: InputPanelProps) {
  return (
    <div className="bg-surface-container-low rounded-xl p-6 space-y-4">
      <h2 className="text-sm font-label text-on-surface-variant uppercase tracking-wider">
        Input Data
      </h2>

      <div className="flex gap-2 flex-wrap">
        {FORMAT_HINTS.map((hint) => (
          <span
            key={hint}
            className="px-2.5 py-1 rounded-full text-xs font-label bg-surface-container-high text-on-surface-variant"
          >
            {hint}
          </span>
        ))}
      </div>

      <textarea
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        rows={10}
        className="w-full bg-surface-container-highest rounded-lg px-4 py-3 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20 resize-y"
        placeholder={`Paste your portfolio data here...\n\nExamples:\n- "VWCE ETF, stocks, ticker VWCE, 8.5% return, balance 15000 as of Jan 2025"\n- CSV: name,type,ticker,balance,date\n  VWCE,STOCKS,VWCE,15000,2025-01-01`}
      />

      <button
        onClick={onParse}
        disabled={!text.trim() || isParsing}
        className="w-full px-4 py-2.5 rounded-lg text-sm font-medium liquid-gradient text-on-primary disabled:opacity-50"
      >
        {isParsing ? "Parsing with AI..." : "Parse with AI"}
      </button>
    </div>
  );
}
