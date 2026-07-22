interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isSubmitting?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Confirmation modal for destructive actions (delete a tag, remove a
 * banner, ...) — see docs/admin-dashboard.md#confirmation-for-destructive-
 * actions. Uses `role="alertdialog"` (not a plain `dialog`) since it always
 * requires an explicit accept/dismiss response, matching the ARIA
 * authoring-practices guidance for confirmation prompts. */
export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  isDestructive = false,
  isSubmitting = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        className="w-full max-w-sm rounded-xl bg-surface p-6 shadow-xl"
      >
        <h2
          id="confirm-dialog-title"
          className="font-display text-lg font-semibold text-text-primary"
        >
          {title}
        </h2>
        <p id="confirm-dialog-message" className="mt-2 text-sm text-text-secondary">
          {message}
        </p>
        {error ? (
          <p role="alert" className="mt-2 text-sm text-danger">
            {error}
          </p>
        ) : null}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className={`rounded-md px-4 py-2 text-sm font-medium text-text-on-primary disabled:cursor-not-allowed disabled:opacity-50 ${
              isDestructive ? "bg-danger hover:bg-danger/90" : "bg-primary hover:bg-primary-hover"
            }`}
          >
            {isSubmitting ? "Please wait…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
