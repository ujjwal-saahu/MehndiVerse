// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ArtistServiceData } from "@/lib/artist-directory-types";

import { CheckAvailabilityWidget } from "./check-availability-widget";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const bookableService: ArtistServiceData = {
  id: "s1",
  name: "Bridal Henna",
  description: null,
  pricing_type: "fixed",
  price_amount: 5000,
  price_min: null,
  price_max: null,
  currency: "INR",
  duration_minutes: 60,
  customer_capacity: 1,
  deposit_required: false,
  deposit_amount: null,
  travel_charge_amount: null,
  cancellation_policy: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const customQuoteService: ArtistServiceData = {
  ...bookableService,
  id: "s2",
  name: "Custom Package",
  pricing_type: "custom_quote",
  price_amount: null,
  duration_minutes: null,
};

describe("CheckAvailabilityWidget", () => {
  it("renders nothing when the artist has no bookable (duration-having) services", () => {
    const { container } = render(
      <CheckAvailabilityWidget artistId="a1" services={[customQuoteService]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("fetches and displays slots for the selected service", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() =>
      Promise.resolve(
        jsonResponse({
          artist_profile_id: "a1",
          service_id: "s1",
          artist_timezone: "UTC",
          slots: [{ start: "2026-03-09T09:00:00Z", end: "2026-03-09T10:00:00Z" }],
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(<CheckAvailabilityWidget artistId="a1" services={[bookableService]} />);

    fireEvent.click(screen.getByRole("button", { name: "Check availability" }));

    await screen.findByText(/Request a booking/);
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/api/artists/a1/availability/slots");
    expect(url).toContain("service_id=s1");

    vi.unstubAllGlobals();
  });

  it("shows a no-slots message when the week is fully booked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            artist_profile_id: "a1",
            service_id: "s1",
            artist_timezone: "UTC",
            slots: [],
          }),
        ),
      ),
    );

    render(<CheckAvailabilityWidget artistId="a1" services={[bookableService]} />);
    fireEvent.click(screen.getByRole("button", { name: "Check availability" }));

    expect(await screen.findByText("No open slots in this week.")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
