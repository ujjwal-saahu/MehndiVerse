// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SavedDesignsView } from "./saved-designs-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleDesign = {
  id: "d1",
  artist_profile_id: null,
  artist_display_name: null,
  title: "Bridal Special",
  status: "published",
  is_featured: false,
  is_premium: false,
  difficulty_level: null,
  body_placement: null,
  thumbnail_url: null,
  view_count: 0,
  like_count: 0,
  save_count: 1,
  created_at: "2026-01-01T00:00:00Z",
};

describe("SavedDesignsView", () => {
  it("shows saved designs once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            items: [sampleDesign],
            page_info: { next_cursor: null, has_more: false },
          }),
        ),
      ),
    );

    render(<SavedDesignsView />);

    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows an empty state when nothing is saved", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
        ),
      ),
    );

    render(<SavedDesignsView />);

    expect(await screen.findByText("No saved designs yet")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows a retry-capable error state when loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ message: "Server unavailable." }, 500))),
    );

    render(<SavedDesignsView />);

    expect(await screen.findByText("Server unavailable.")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
