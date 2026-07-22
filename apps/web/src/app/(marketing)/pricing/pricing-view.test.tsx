// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PricingView } from "./pricing-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const customerPlan = {
  id: "plan-1",
  name: "Premium Monthly",
  slug: "premium-monthly",
  target_role: "customer",
  price_amount: 199,
  currency: "INR",
  billing_interval: "monthly",
  features: { premium_design_access: true, download_limit_per_month: 100 },
  is_active: true,
};

const artistPlan = {
  id: "plan-2",
  name: "Professional Monthly",
  slug: "professional-monthly",
  target_role: "artist",
  price_amount: 499,
  currency: "INR",
  billing_interval: "monthly",
  features: { portfolio_limit: null },
  is_active: true,
};

function stubFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.includes("/api/subscriptions/plans")) {
        return Promise.resolve(jsonResponse([customerPlan, artistPlan]));
      }
      if (url.includes("/api/auth/me")) {
        return Promise.resolve(new Response(null, { status: 401 }));
      }
      return Promise.resolve(jsonResponse({}));
    }),
  );
}

describe("PricingView", () => {
  it("shows customer plans by default", async () => {
    stubFetch();
    render(<PricingView />);

    expect(await screen.findByText("Premium Monthly")).toBeInTheDocument();
    expect(screen.queryByText("Professional Monthly")).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("switches to artist plans on tab click", async () => {
    stubFetch();
    render(<PricingView />);
    await screen.findByText("Premium Monthly");

    fireEvent.click(screen.getByRole("button", { name: "For artists" }));

    expect(await screen.findByText("Professional Monthly")).toBeInTheDocument();
    expect(screen.queryByText("Premium Monthly")).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("prompts an unauthenticated visitor to log in instead of showing Subscribe", async () => {
    stubFetch();
    render(<PricingView />);

    expect(await screen.findByRole("link", { name: "Log in to subscribe" })).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
