"use client";

import Link from "next/link";
import { NavLinks } from "./header/nav-links";
import { ThemeToggle } from "./theme-toggle";
import { MobileNav } from "./mobile-nav";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-glass bg-surface-primary/40 backdrop-filter backdrop-blur shadow-md transition-colors duration-300">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          {/* Logo */}
          <Link
            href="/"
            className="flex flex-shrink-0 items-center gap-2 text-lg sm:text-xl font-bold text-text-primary transition-colors hover:text-accent-conservative"
          >
            <span className="text-xl sm:text-2xl">🏛️</span>
            <span className="hidden sm:inline">TrueCivic</span>
          </Link>

          {/* Nav Links (Desktop) */}
          <NavLinks />

          {/* Right Actions */}
          <div className="flex items-center gap-2 sm:gap-4">
            <ThemeToggle />
            <MobileNav />
          </div>
        </div>
      </div>
    </header>
  );
}
