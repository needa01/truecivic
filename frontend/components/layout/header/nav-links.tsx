"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export type NavigationSection = "bills" | "votes" | "debates" | "meetings" | "members";

const sections: Array<{ href: string; label: string; section: NavigationSection }> = [
  { href: "/bills", label: "Bills", section: "bills" },
  { href: "/votes", label: "Votes", section: "votes" },
  { href: "/debates", label: "Debates", section: "debates" },
  { href: "/committees", label: "Meetings", section: "meetings" },
  { href: "/politicians", label: "Members", section: "members" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="hidden items-center gap-2 text-sm md:flex">
      {sections.map(({ href, label, section }) => {
        const isActive = pathname.startsWith(href);
        return (
          <Link
            key={section}
            href={href}
            className={cn(
              "relative px-4 py-2 font-medium transition-colors",
              isActive
                ? "text-text-primary"
                : "text-text-secondary hover:text-text-primary"
            )}
            data-section={section}
            aria-current={isActive ? "page" : undefined}
          >
            {label}
            {isActive && (
              <span
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-accent-liberal to-accent-conservative"
                style={{
                  animation: "slide-in 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                }}
              />
            )}
          </Link>
        );
      })}
    </nav>
  );
}

