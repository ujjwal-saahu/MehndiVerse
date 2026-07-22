"use client";

import { useState } from "react";

import { mutateJson } from "@/lib/gallery-client";

interface ReportButtonProps {
  /** The `/api/...` proxy path this hits, e.g. `/api/designs/{id}/report`. */
  endpoint: string;
  label?: string;
  promptMessage?: string;
  className?: string;
}

/** A minimal report control shared by design/comment/user reporting — see
 * docs/community-and-trust.md#5-reports-enter-a-moderation-queue. Mirrors
 * the existing message-report pattern in booking-conversation.tsx (a plain
 * `window.prompt` for the reason) so all four report surfaces behave the
 * same way from the reporter's point of view. */
export function ReportButton({
  endpoint,
  label = "Report",
  promptMessage = "Why are you reporting this?",
  className = "text-xs text-text-secondary hover:underline",
}: ReportButtonProps) {
  const [state, setState] = useState<"idle" | "pending" | "done" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const submit = () => {
    const reason = window.prompt(promptMessage);
    if (!reason) return;

    setState("pending");
    mutateJson<{ status: string }>(endpoint, "POST", { reason })
      .then(() => {
        setState("done");
        setMessage("Thanks — our team will take a look.");
      })
      .catch((error: Error) => {
        setState("error");
        setMessage(error.message);
      });
  };

  if (state === "done" || state === "error") {
    return (
      <span className={`text-xs ${state === "error" ? "text-danger" : "text-text-secondary"}`}>
        {message}
      </span>
    );
  }

  return (
    <button
      type="button"
      disabled={state === "pending"}
      onClick={submit}
      className={`${className} disabled:cursor-not-allowed disabled:opacity-60`}
    >
      {label}
    </button>
  );
}
