"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import { Header } from "./header";
import { Sidebar } from "./sidebar";

interface DashboardShellProps {
  email: string;
  role: string;
  children: ReactNode;
}

/** Responsive dashboard shell: a fixed sidebar alongside content on large
 * screens, collapsing to a header-triggered drawer below the `lg` breakpoint
 * (see packages/design-tokens/src/breakpoints.ts). */
export function DashboardShell({ email, role, children }: DashboardShellProps) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-full flex-col">
      <Header email={email} role={role} onOpenSidebar={() => setIsMobileNavOpen(true)} />
      <div className="flex flex-1">
        <Sidebar role={role} className="hidden w-64 shrink-0 border-r border-border lg:flex" />

        {isMobileNavOpen ? (
          <div className="fixed inset-0 z-40 flex lg:hidden">
            <button
              type="button"
              aria-label="Close navigation menu"
              className="absolute inset-0 bg-black/40"
              onClick={() => setIsMobileNavOpen(false)}
            />
            <div className="relative z-10 h-full w-64 bg-surface shadow-xl">
              <Sidebar role={role} />
            </div>
          </div>
        ) : null}

        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
