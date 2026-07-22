interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

/** Shown when a view failed to load its data — distinct from [EmptyState]
 * ("loaded, nothing there"); always offers a retry action when one is
 * available. */
export function ErrorState({ title = "Something went wrong", message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-16 text-center" role="alert">
      <h2 className="font-display text-xl font-semibold text-text-primary">{title}</h2>
      <p className="max-w-md text-text-secondary">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
