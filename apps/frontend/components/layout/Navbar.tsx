"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStatus } from "@/lib/hooks";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/assets", label: "Assets" },
  { href: "/fire-calculator", label: "FIRE Calculator" },
  { href: "/import", label: "Smart Import" },
  { href: "/login", label: "Owner Login" },
];

export function Navbar() {
  const pathname = usePathname();
  const { data: auth } = useAuthStatus();
  const isOwner = auth?.authenticated ?? false;

  return (
    <nav className="fixed top-0 left-0 right-0 z-40 h-14 bg-surface-container/80 backdrop-blur-xl border-b border-outline-variant/15">
      <div className="max-w-7xl mx-auto h-full flex items-center gap-8 px-4 md:px-8">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <div className="w-7 h-7 rounded-lg liquid-gradient flex items-center justify-center">
            <span className="text-on-primary font-headline font-bold text-sm">F</span>
          </div>
          <span className="font-headline font-bold text-on-surface text-lg tracking-tight">
            Fineas
          </span>
          <span
            className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-label tracking-wider uppercase ${
              isOwner
                ? "bg-primary/15 text-primary"
                : "bg-tertiary-container/40 text-tertiary"
            }`}
            title={
              isOwner
                ? "Viewing real owner data"
                : "Viewing demo fixtures — log in to see real data"
            }
          >
            {isOwner ? "Live" : "Demo"}
          </span>
        </Link>

        <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
          {links.map(({ href, label }) => {
            const isActive =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`px-3 py-1.5 rounded-lg text-sm font-label transition-colors whitespace-nowrap ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/50"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
