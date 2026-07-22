// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ServicesManagerView } from "./services-manager-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleService = {
  id: "s1",
  name: "Bridal Henna Package",
  description: null,
  pricing_type: "fixed",
  price_amount: 5000,
  price_min: null,
  price_max: null,
  currency: "INR",
  duration_minutes: 120,
  customer_capacity: 1,
  deposit_required: false,
  deposit_amount: null,
  travel_charge_amount: null,
  cancellation_policy: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("ServicesManagerView", () => {
  it("shows an empty state when there are no services", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([]))),
    );

    render(<ServicesManagerView />);

    expect(await screen.findByText("No services yet")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("lists existing services", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([sampleService]))),
    );

    render(<ServicesManagerView />);

    expect(await screen.findByText("Bridal Henna Package")).toBeInTheDocument();
    expect(screen.getByText("INR 5000")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("deactivates a service", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "PATCH") {
        return Promise.resolve(jsonResponse({ ...sampleService, is_active: false }));
      }
      return Promise.resolve(jsonResponse([sampleService]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ServicesManagerView />);
    await screen.findByText("Bridal Henna Package");

    fireEvent.click(screen.getByRole("button", { name: "Deactivate" }));

    expect(await screen.findByText("Inactive")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("creates a new service via the form", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ ...sampleService, id: "s2", name: "Party Henna" }));
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ServicesManagerView />);
    await screen.findByText("No services yet");

    fireEvent.click(screen.getByRole("button", { name: "New service" }));
    fireEvent.change(screen.getByLabelText("Service name"), {
      target: { value: "Party Henna" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create service" }));

    expect(await screen.findByText("Party Henna")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
