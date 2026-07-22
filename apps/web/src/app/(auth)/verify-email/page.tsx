"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";
  const [sent, setSent] = useState(false);

  const resend = async () => {
    await fetch("/api/auth/verify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    setSent(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">Check your email</h1>
      <p className="text-text-secondary">
        We sent a verification link to {email || "your email address"}.
      </p>
      {sent ? <p className="text-sm text-success">Verification email sent again.</p> : null}
      <button
        type="button"
        onClick={resend}
        className="w-full rounded-md border border-border px-4 py-2 font-medium text-text-primary hover:bg-surface-variant"
      >
        Resend verification email
      </button>
      <Link href="/login" className="text-sm text-text-secondary hover:text-text-primary">
        Back to login
      </Link>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
