"use client";

import { useEffect, useRef } from "react";

interface GlassModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function GlassModal({ open, onClose, title, children }: GlassModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="glass-panel rounded-2xl w-full max-w-lg mx-4 border border-outline-variant/15 overflow-hidden">
        {/* Top rim highlight */}
        <div className="h-px bg-gradient-to-r from-transparent via-primary-fixed/30 to-transparent" />
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-headline font-bold text-on-surface">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="text-on-surface-variant hover:text-on-surface transition-colors p-1"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
