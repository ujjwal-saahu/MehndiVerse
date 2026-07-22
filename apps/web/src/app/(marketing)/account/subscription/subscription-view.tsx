"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import { formatMinorAmount } from "@/lib/payment-types";
import type {
  BillingHistoryItemData,
  MySubscriptionData,
  SubscriptionStatusHistoryData,
} from "@/lib/subscription-types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: MySubscriptionData };

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  cancelled: "Cancelled",
  expired: "Expired",
  past_due: "Payment overdue — grace period",
  trialing: "Awaiting first payment",
};

export function SubscriptionView() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [billingHistory, setBillingHistory] = useState<BillingHistoryItemData[]>([]);
  const [statusHistory, setStatusHistory] = useState<SubscriptionStatusHistoryData[]>([]);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [showStatusHistory, setShowStatusHistory] = useState(false);

  const load = useCallback(() => {
    fetch("/api/subscriptions/me")
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error())))
      .then((data: MySubscriptionData) => setState({ status: "ready", data }))
      .catch(() => setState({ status: "error", message: "Could not load your subscription." }));
  }, []);

  useEffect(load, [load]);

  useEffect(() => {
    fetch("/api/subscriptions/me/billing-history")
      .then((response) => (response.ok ? response.json() : []))
      .then(setBillingHistory)
      .catch(() => setBillingHistory([]));
  }, []);

  useEffect(() => {
    if (state.status !== "ready" || !state.data.subscription) return;
    const subscriptionId = state.data.subscription.id;
    fetch(`/api/subscriptions/${subscriptionId}/status-history`)
      .then((response) => (response.ok ? response.json() : []))
      .then(setStatusHistory)
      .catch(() => setStatusHistory([]));
  }, [state]);

  const cancel = async () => {
    if (
      !window.confirm("Cancel your subscription? You'll keep access until the current period ends.")
    ) {
      return;
    }
    setIsCancelling(true);
    setCancelError(null);
    try {
      const response = await fetch("/api/subscriptions/me/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const body = await response.json();
      if (!response.ok) {
        setCancelError(body.message);
        return;
      }
      load();
    } finally {
      setIsCancelling(false);
    }
  };

  if (state.status === "loading") {
    return (
      <div className="mt-6" aria-label="Loading subscription" role="status">
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="mt-6">
        <ErrorState message={state.message} onRetry={load} />
      </div>
    );
  }

  const { subscription, entitlements } = state.data;

  return (
    <div className="mt-6">
      {subscription ? (
        <div className="rounded-xl border border-border bg-surface p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-text-primary">{subscription.plan.name}</h2>
            <span className="rounded-full bg-surface-variant px-3 py-1 text-xs font-medium text-text-secondary">
              {STATUS_LABELS[subscription.status] ?? subscription.status}
            </span>
          </div>
          <p className="mt-2 text-sm text-text-secondary">
            {subscription.cancel_at_period_end
              ? `Access ends ${new Date(subscription.current_period_end).toLocaleDateString()}`
              : `Renews ${new Date(subscription.current_period_end).toLocaleDateString()}`}
          </p>
          {subscription.status === "past_due" && subscription.grace_period_ends_at ? (
            <p className="mt-1 text-sm text-danger">
              Your last payment failed. Please retry before{" "}
              {new Date(subscription.grace_period_ends_at).toLocaleDateString()} to keep your
              benefits.
            </p>
          ) : null}

          {cancelError ? <p className="mt-2 text-sm text-danger">{cancelError}</p> : null}

          {!subscription.cancel_at_period_end &&
          (subscription.status === "active" || subscription.status === "past_due") ? (
            <button
              type="button"
              onClick={() => void cancel()}
              disabled={isCancelling}
              className="mt-4 rounded-md border border-danger px-4 py-2 text-sm font-medium text-danger hover:bg-danger-surface disabled:opacity-50"
            >
              Cancel subscription
            </button>
          ) : null}

          <button
            type="button"
            onClick={() => setShowStatusHistory((v) => !v)}
            className="mt-4 block text-sm text-primary hover:underline"
          >
            {showStatusHistory ? "Hide status history" : "Show status history"}
          </button>
          {showStatusHistory ? (
            <ul className="mt-2 space-y-1 text-xs text-text-secondary">
              {statusHistory.map((h) => (
                <li key={h.id}>
                  {new Date(h.created_at).toLocaleString()} — {h.from_status ?? "(new)"} →{" "}
                  {h.to_status}
                  {h.reason ? ` (${h.reason})` : ""}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-surface p-6">
          <p className="text-text-primary">You&apos;re on the free plan.</p>
          <Link href="/pricing" className="mt-3 inline-block text-sm text-primary hover:underline">
            View plans &amp; upgrade
          </Link>
        </div>
      )}

      <div className="mt-4 rounded-xl border border-border bg-surface p-6">
        <h3 className="text-sm font-medium text-text-secondary">Current entitlements</h3>
        <ul className="mt-2 space-y-1 text-sm text-text-primary">
          {Object.entries(entitlements).map(([key, value]) => (
            <li key={key}>
              {key.replace(/_/g, " ")}: {value === null ? "Unlimited" : String(value)}
            </li>
          ))}
        </ul>
      </div>

      <section className="mt-6">
        <h2 className="font-medium text-text-primary">Billing history</h2>
        {billingHistory.length === 0 ? (
          <p className="mt-2 text-sm text-text-secondary">No subscription payments yet.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-2">
            {billingHistory.map((item) => (
              <li
                key={item.payment_id}
                className="rounded-md border border-border bg-surface p-3 text-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-text-primary">
                    {item.plan_name ?? "Subscription"} —{" "}
                    {formatMinorAmount(item.amount, item.currency)}
                  </span>
                  <span className="text-xs text-text-secondary">{item.status}</span>
                </div>
                {item.failure_reason ? (
                  <p className="mt-1 text-xs text-danger">{item.failure_reason}</p>
                ) : null}
                <p className="mt-1 text-xs text-text-secondary">
                  {new Date(item.created_at).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
