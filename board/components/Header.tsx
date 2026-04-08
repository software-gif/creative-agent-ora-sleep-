"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Header() {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Board", icon: "M4 6h16M4 12h16M4 18h7" },
    { href: "/library", label: "Library", icon: "M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" },
    { href: "/approved", label: "Approved", icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-3">
      <nav className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-3">
            <span className="text-lg font-bold text-primary tracking-tight">
              Ora Sleep
            </span>
            <div className="border-l border-border pl-3">
              <span className="text-[10px] font-semibold text-accent uppercase tracking-widest">
                Creative Board
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-1 bg-background rounded-lg p-0.5">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md transition-all ${
                    isActive
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-foreground"
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-3.5 h-3.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                  </svg>
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted">
            Schlafkomfort aus der Schweiz
          </span>
        </div>
      </nav>
    </header>
  );
}
