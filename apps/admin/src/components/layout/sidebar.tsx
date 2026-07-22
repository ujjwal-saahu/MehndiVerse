"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { navItemsForRole } from "./nav-items";

/** Permission-aware navigation: only nav items whose `roles` include the
 * current staff member's role are rendered. This is a UX convenience, not
 * the security boundary — every destination re-checks the role
 * server-side (see docs/authentication.md). */
export function Sidebar({ role, className = "" }: { role: string; className?: string }) {
  const pathname = usePathname();
  const items = navItemsForRole(role);

  return (
    <nav aria-label="Admin navigation" className={`flex flex-col gap-1 p-4 ${className}`}>
      {items.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-primary text-text-on-primary"
                : "text-text-primary hover:bg-surface-variant"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
