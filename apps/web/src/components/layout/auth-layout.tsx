import Link from "next/link";
import type { ReactNode } from "react";

/** Distraction-free layout for login/register/forgot-password/verify-email —
 * a centered card with just the wordmark, no public nav/footer chrome.
 * Route-group layout for `(auth)` — see src/app/(auth)/layout.tsx.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-background px-4 py-12">
      <Link href="/" className="mb-8 font-display text-2xl font-semibold text-primary">
        MehndiVerse
      </Link>
      <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-md">
        {children}
      </div>
    </div>
  );
}
