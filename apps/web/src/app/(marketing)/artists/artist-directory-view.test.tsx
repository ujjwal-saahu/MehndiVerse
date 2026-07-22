// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ArtistDirectoryView } from "./artist-directory-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleArtist = {
  id: "a1",
  display_name: "Priya Sharma",
  headline: "Bridal henna specialist",
  avatar_url: null,
  city: "Jaipur",
  country: "IN",
  years_experience: 10,
  is_verified: true,
  rating_average: 4.8,
  rating_count: 25,
  is_accepting_bookings: true,
};

describe("ArtistDirectoryView", () => {
  it("shows artists once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            items: [sampleArtist],
            page_info: { next_cursor: null, has_more: false },
          }),
        ),
      ),
    );

    render(<ArtistDirectoryView />);

    expect(await screen.findByText("Priya Sharma")).toBeInTheDocument();
    expect(screen.getByText("Bridal henna specialist")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows an empty state when nothing matches", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
        ),
      ),
    );

    render(<ArtistDirectoryView />);

    expect(await screen.findByText("No artists found")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("re-searches with the submitted filters", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url.includes("city=Mumbai")) {
        return Promise.resolve(
          jsonResponse({
            items: [{ ...sampleArtist, id: "a2", display_name: "Second Artist", city: "Mumbai" }],
            page_info: { next_cursor: null, has_more: false },
          }),
        );
      }
      return Promise.resolve(
        jsonResponse({ items: [sampleArtist], page_info: { next_cursor: null, has_more: false } }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ArtistDirectoryView />);
    await screen.findByText("Priya Sharma");

    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Mumbai" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Second Artist")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
