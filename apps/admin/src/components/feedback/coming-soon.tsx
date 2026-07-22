import { EmptyState } from "./empty-state";

/** A dashboard section not built yet (Phase 4 is UI shells only — see
 * docs/design-system.md). Deliberately shows an empty state rather than
 * invented rows. */
export function ComingSoon({ title, message }: { title: string; message: string }) {
  return (
    <div>
      <h1 className="font-display text-2xl font-semibold text-text-primary">{title}</h1>
      <div className="mt-6 rounded-xl border border-border bg-surface">
        <EmptyState title={title} message={message} />
      </div>
    </div>
  );
}
