"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/feedback/skeleton";
import { loadRazorpayScript } from "@/lib/razorpay-checkout";
import type {
  CheckoutOrderData,
  CouponValidateData,
  SubscriptionPlanData,
} from "@/lib/subscription-types";
import { useCurrentUser } from "@/lib/use-current-user";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; plans: SubscriptionPlanData[] };

function formatPrice(plan: SubscriptionPlanData): string {
  if (plan.price_amount <= 0) return "Free";
  const perInterval = plan.billing_interval === "yearly" ? "/year" : "/month";
  return `${plan.currency} ${plan.price_amount.toFixed(2)}${perInterval}`;
}

function featureLines(features: Record<string, unknown> | null): string[] {
  if (!features) return [];
  const lines: string[] = [];
  if (features.premium_design_access) lines.push("Access to premium designs");
  if (typeof features.download_limit_per_month === "number") {
    lines.push(`${features.download_limit_per_month} downloads / month`);
  }
  if (typeof features.ai_credits_per_month === "number") {
    lines.push(`${features.ai_credits_per_month} AI credits / month`);
  }
  if (features.portfolio_limit === null) {
    lines.push("Unlimited portfolio designs");
  } else if (typeof features.portfolio_limit === "number") {
    lines.push(`Up to ${features.portfolio_limit} published designs`);
  }
  return lines;
}

export function PricingView() {
  const user = useCurrentUser();
  const [state, setState] = useState<State>({ status: "loading" });
  const [couponCode, setCouponCode] = useState("");
  const [couponPreview, setCouponPreview] = useState<Record<string, CouponValidateData>>({});
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);

  // `fetchOnly` never calls setState synchronously — only from inside its
  // `.then`/`.catch` — so the mount effect below doesn't trigger a
  // cascading render. `load` (used by the retry button) resets to
  // "loading" first; it's only ever invoked from an event handler. Mirrors
  // apps/admin's `useAdminList` hook.
  const fetchOnly = useCallback(() => {
    fetch("/api/subscriptions/plans")
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error())))
      .then((plans: SubscriptionPlanData[]) => setState({ status: "ready", plans }))
      .catch(() =>
        setState({ status: "error", message: "Could not load plans. Please try again." }),
      );
  }, []);

  const load = useCallback(() => {
    setState({ status: "loading" });
    fetchOnly();
  }, [fetchOnly]);

  useEffect(() => {
    fetchOnly();
  }, [fetchOnly]);

  // Artists land on the "For artists" tab by default; picked once at the
  // moment `user` first resolves (a render-time default, not state kept in
  // sync with `user` via an effect).
  const defaultTab =
    user?.role === "artist" || user?.role === "verified_artist" ? "artist" : "customer";
  const [tabOverride, setTabOverride] = useState<"customer" | "artist" | null>(null);
  const tab = tabOverride ?? defaultTab;
  const setTab = (next: "customer" | "artist") => setTabOverride(next);

  const visiblePlans = useMemo(
    () => (state.status === "ready" ? state.plans.filter((p) => p.target_role === tab) : []),
    [state, tab],
  );

  const applyCoupon = async (planId: string) => {
    if (!couponCode) return;
    const response = await fetch("/api/coupons/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: couponCode, plan_id: planId }),
    });
    if (!response.ok) return;
    const preview = (await response.json()) as CouponValidateData;
    setCouponPreview((current) => ({ ...current, [planId]: preview }));
  };

  const subscribe = async (plan: SubscriptionPlanData) => {
    setCheckoutError(null);
    setBusyPlanId(plan.id);
    try {
      const response = await fetch("/api/subscriptions/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan_id: plan.id,
          coupon_code: couponPreview[plan.id]?.valid ? couponCode : undefined,
        }),
      });
      const body = (await response.json()) as CheckoutOrderData | { message: string };
      if (!response.ok) {
        setCheckoutError((body as { message: string }).message);
        return;
      }
      const order = body as CheckoutOrderData;
      await loadRazorpayScript();
      const checkout = new window.Razorpay!({
        key: order.provider_key_id,
        amount: order.amount,
        currency: order.currency,
        order_id: order.provider_order_id,
        name: "MehndiVerse",
        description: `${plan.name} subscription`,
        handler: () => setAwaitingConfirmation(true),
      });
      checkout.open();
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : "Could not start checkout.");
    } finally {
      setBusyPlanId(null);
    }
  };

  return (
    <div className="mt-8">
      <div className="flex gap-2">
        {(["customer", "artist"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium ${
              t === tab
                ? "bg-primary text-text-on-primary"
                : "bg-surface-variant text-text-secondary hover:bg-surface-variant/80"
            }`}
          >
            {t === "customer" ? "For customers" : "For artists"}
          </button>
        ))}
      </div>

      {checkoutError ? <p className="mt-4 text-sm text-danger">{checkoutError}</p> : null}
      {awaitingConfirmation ? (
        <p className="mt-4 text-sm text-text-secondary">
          Waiting for your payment to be confirmed — check{" "}
          <Link href="/account/subscription" className="text-primary hover:underline">
            My subscription
          </Link>{" "}
          shortly.
        </p>
      ) : null}

      {state.status === "loading" ? (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-64" aria-label="Loading plan" />
          ))}
        </div>
      ) : state.status === "error" ? (
        <div className="mt-6">
          <ErrorState message={state.message} onRetry={load} />
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {visiblePlans.map((plan) => {
            const preview = couponPreview[plan.id];
            return (
              <div
                key={plan.id}
                className="flex flex-col rounded-xl border border-border bg-surface p-6"
              >
                <h3 className="font-display text-lg font-semibold text-text-primary">
                  {plan.name}
                </h3>
                <p className="mt-1 text-2xl font-semibold text-text-primary">{formatPrice(plan)}</p>
                <ul className="mt-4 flex-1 space-y-1 text-sm text-text-secondary">
                  {featureLines(plan.features).map((line) => (
                    <li key={line}>• {line}</li>
                  ))}
                </ul>

                {plan.price_amount > 0 ? (
                  <>
                    <div className="mt-4 flex gap-2">
                      <input
                        type="text"
                        value={couponCode}
                        onChange={(event) => setCouponCode(event.target.value)}
                        placeholder="Coupon code"
                        aria-label="Coupon code"
                        className="flex-1 rounded-md border border-border px-2 py-1.5 text-sm text-text-primary"
                      />
                      <button
                        type="button"
                        onClick={() => void applyCoupon(plan.id)}
                        className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-surface-variant"
                      >
                        Apply
                      </button>
                    </div>
                    {preview ? (
                      <p
                        className={`mt-1 text-xs ${preview.valid ? "text-success" : "text-danger"}`}
                      >
                        {preview.valid
                          ? `Coupon applied — final price ${plan.currency} ${preview.final_amount?.toFixed(2)}`
                          : preview.message}
                      </p>
                    ) : null}

                    {user ? (
                      <button
                        type="button"
                        disabled={busyPlanId === plan.id}
                        onClick={() => void subscribe(plan)}
                        className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-on-primary disabled:opacity-50"
                      >
                        {busyPlanId === plan.id ? "Starting checkout…" : "Subscribe"}
                      </button>
                    ) : (
                      <Link
                        href="/login"
                        className="mt-4 rounded-md bg-primary px-4 py-2 text-center text-sm font-medium text-text-on-primary"
                      >
                        Log in to subscribe
                      </Link>
                    )}
                  </>
                ) : (
                  <p className="mt-4 text-sm text-text-secondary">
                    Free — no checkout needed. This is your plan by default until you upgrade.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
