import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  message?: string;
  action?: ReactNode;
}

/** Shown when a view legitimately has nothing to display yet — never filled
 * with fake data. See docs/design-system.md. */
export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
      <h2 className="font-display text-xl font-semibold text-text-primary">{title}</h2>
      {message ? <p className="max-w-md text-text-secondary">{message}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
