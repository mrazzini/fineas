"use client";

interface ConfirmBarProps {
  onDiscard: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
  disabled: boolean;
}

export function ConfirmBar({ onDiscard, onConfirm, isConfirming, disabled }: ConfirmBarProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 bg-surface-container/80 backdrop-blur-xl border-t border-outline-variant/15">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex items-center justify-end gap-3">
        <button
          onClick={onDiscard}
          className="px-4 py-2 rounded-lg text-sm text-on-surface-variant hover:text-on-surface transition-colors"
        >
          Discard
        </button>
        <button
          onClick={onConfirm}
          disabled={disabled || isConfirming}
          className="px-6 py-2 rounded-lg text-sm font-medium liquid-gradient text-on-primary disabled:opacity-50"
        >
          {isConfirming ? "Saving..." : "Confirm & Save"}
        </button>
      </div>
    </div>
  );
}
