// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RequestBookingButton } from "./request-booking-button";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe("RequestBookingButton", () => {
  it("is disabled with the not-accepting label when the artist isn't accepting bookings", () => {
    render(<RequestBookingButton artistId="a1" isAcceptingBookings={false} />);
    expect(screen.getByRole("button", { name: "Not accepting bookings" })).toBeDisabled();
  });

  it("creates a draft booking and navigates to its detail page", async () => {
    const fetchSpy = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(() =>
      Promise.resolve(new Response(JSON.stringify({ id: "b1", status: "draft" }), { status: 201 })),
    );
    vi.stubGlobal("fetch", fetchSpy);

    render(<RequestBookingButton artistId="a1" isAcceptingBookings={true} />);
    fireEvent.click(screen.getByRole("button", { name: "Request a booking" }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/bookings/b1"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/bookings",
      expect.objectContaining({ method: "POST" }),
    );

    vi.unstubAllGlobals();
  });

  it("shows the backend's error message when creation fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({ message: "This artist is not currently accepting bookings." }),
            {
              status: 409,
            },
          ),
        ),
      ),
    );

    render(<RequestBookingButton artistId="a1" isAcceptingBookings={true} />);
    fireEvent.click(screen.getByRole("button", { name: "Request a booking" }));

    expect(
      await screen.findByText("This artist is not currently accepting bookings."),
    ).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
