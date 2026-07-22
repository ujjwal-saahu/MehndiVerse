"use client";

import { useState } from "react";

export function DataExportView() {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");

  const onDownload = async () => {
    setState("loading");
    const response = await fetch("/api/account/data-export");
    if (!response.ok) {
      setState("error");
      return;
    }
    const payload = await response.json();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "mehndiverse-account-data.json";
    link.click();
    URL.revokeObjectURL(url);
    setState("idle");
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-text-secondary">
        Download a copy of your profile, bookings, payments, reviews, support requests, and consent
        history as a JSON file.
      </p>
      {state === "error" ? (
        <p role="alert" className="text-sm text-danger">
          Couldn&apos;t generate your export. Please try again.
        </p>
      ) : null}
      <button
        type="button"
        onClick={onDownload}
        disabled={state === "loading"}
        className="w-fit rounded-md bg-primary px-4 py-2 font-medium text-text-on-primary hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        {state === "loading" ? "Preparing…" : "Download my data"}
      </button>
    </div>
  );
}
