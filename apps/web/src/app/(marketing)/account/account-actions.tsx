"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function AccountActions() {
  const router = useRouter();
  const [confirmingDeletion, setConfirmingDeletion] = useState(false);
  const [deletionMessage, setDeletionMessage] = useState<string | null>(null);

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  };

  const deleteAccount = async () => {
    const response = await fetch("/api/auth/delete-account", { method: "POST" });
    const body = (await response.json()) as { message: string };
    setDeletionMessage(body.message);
    if (response.ok) {
      setTimeout(() => {
        router.push("/login");
        router.refresh();
      }, 1500);
    }
  };

  return (
    <div className="flex flex-col items-start gap-4">
      <button
        type="button"
        onClick={logout}
        className="rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-variant"
      >
        Log out
      </button>

      <Link
        href="/account/data-export"
        className="text-sm font-medium text-primary hover:underline"
      >
        Download my data
      </Link>

      {deletionMessage ? (
        <p className="text-sm text-text-secondary">{deletionMessage}</p>
      ) : confirmingDeletion ? (
        <div className="flex flex-col gap-2 rounded-md border border-danger bg-danger-surface p-4">
          <p className="text-sm text-text-primary">
            This will request deletion of your account. Continue?
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={deleteAccount}
              className="rounded-md bg-danger px-3 py-1.5 text-sm font-medium text-text-on-primary"
            >
              Yes, delete my account
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDeletion(false)}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-variant"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirmingDeletion(true)}
          className="text-sm text-danger hover:underline"
        >
          Delete my account
        </button>
      )}
    </div>
  );
}
