"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/feedback/error-state";

/** Next.js route-segment error boundary — catches rendering/data errors
 * anywhere in this route group and offers a retry via `reset()`. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Errors caught here still need surfacing somewhere observable — a
    // later phase wires this into Sentry (see docs/security-baseline.md).
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <ErrorState message="We couldn't load this page. Please try again." onRetry={reset} />
    </div>
  );
}
