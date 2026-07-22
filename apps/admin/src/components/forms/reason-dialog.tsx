"use client";

import { useState } from "react";

interface ReasonDialogProps {
  isOpen: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  isSubmitting?: boolean;
  error?: string | null;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

/** Prompts for a mandatory reason before a suspension/rejection/moderation
 * action proceeds — see docs/admin-dashboard.md#mandatory-reasons. The
 * confirm button stays disabled until the trimmed reason is non-empty, the
 * same rule the backend enforces server-side (`Field(min_length=1)` on
 * every reason-taking request schema) — this is a UX convenience, not the
 * actual boundary. */
export function ReasonDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Submit",
  isSubmitting = false,
  error = null,
  onConfirm,
  onCancel,
}: ReasonDialogProps) {
  const [reason, setReason] = useState("");
  // Resets the field when the dialog transitions to open — adjusting state
  // during render (React's documented pattern for "reset state when a prop
  // changes") rather than in a `useEffect`, so opening for a new target
  // never briefly shows the previous target's typed text.
  const [wasOpen, setWasOpen] = useState(isOpen);
  if (isOpen !== wasOpen) {
    setWasOpen(isOpen);
    if (isOpen) setReason("");
  }

  if (!isOpen) return null;

  const trimmed = reason.trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reason-dialog-title"
        className="w-full max-w-md rounded-xl bg-surface p-6 shadow-xl"
      >
        <h2
          id="reason-dialog-title"
          className="font-display text-lg font-semibold text-text-primary"
        >
          {title}
        </h2>
        {description ? <p className="mt-1 text-sm text-text-secondary">{description}</p> : null}

        <label
          htmlFor="reason-dialog-textarea"
          className="mt-4 block text-sm font-medium text-text-primary"
        >
          Reason
        </label>
        <textarea
          id="reason-dialog-textarea"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          required
          rows={3}
          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-text-primary focus:border-focus-ring focus:outline-none focus:ring-2 focus:ring-focus-ring"
        />
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
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(trimmed)}
            disabled={isSubmitting || trimmed.length === 0}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? "Please wait…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
