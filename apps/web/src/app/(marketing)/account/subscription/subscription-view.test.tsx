// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SubscriptionView } from "./subscription-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("SubscriptionView", () => {
  it("shows a free-plan message when there is no active subscription", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/api/subscriptions/me/billing-history")) {
          return Promise.resolve(jsonResponse([]));
        }
        if (url.includes("/api/subscriptions/me")) {
          return Promise.resolve(
            jsonResponse({
              subscription: null,
              entitlements: { premium_design_access: false, download_limit_per_month: 5 },
            }),
          );
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    render(<SubscriptionView />);

    expect(await screen.findByText("You're on the free plan.")).toBeInTheDocument();
    expect(screen.getByText(/download limit per month: 5/)).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows the active plan and a cancel button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/status-history")) return Promise.resolve(jsonResponse([]));
        if (url.includes("/billing-history")) return Promise.resolve(jsonResponse([]));
        if (url.includes("/api/subscriptions/me")) {
          return Promise.resolve(
            jsonResponse({
              subscription: {
                id: "sub-1",
                user_id: "u1",
                plan: {
                  id: "plan-1",
                  name: "Premium Monthly",
                  slug: "premium-monthly",
                  target_role: "customer",
                  price_amount: 199,
                  currency: "INR",
                  billing_interval: "monthly",
                  features: {},
                  is_active: true,
                },
                status: "active",
                current_period_start: "2026-07-01T00:00:00Z",
                current_period_end: "2026-08-01T00:00:00Z",
                cancel_at_period_end: false,
                grace_period_ends_at: null,
                started_at: "2026-07-01T00:00:00Z",
                cancelled_at: null,
              },
              entitlements: {},
            }),
          );
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    render(<SubscriptionView />);

    expect(await screen.findByText("Premium Monthly")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel subscription" })).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
