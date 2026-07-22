// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DiscoverView } from "./discover-view";

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

const sampleDesign = {
  id: "d1",
  artist_profile_id: "a1",
  artist_display_name: "Asha",
  title: "Bridal Special",
  status: "published",
  is_featured: false,
  is_premium: false,
  difficulty_level: null,
  body_placement: null,
  thumbnail_url: "/thumb.jpg",
  view_count: 3,
  created_at: "2026-01-01T00:00:00Z",
};

describe("DiscoverView", () => {
  it("shows the home feed sections once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/api/categories")) return Promise.resolve(jsonResponse([]));
        if (url.includes("/api/designs/home-feed")) {
          return Promise.resolve(
            jsonResponse({ latest: [sampleDesign], featured: [], trending: [] }),
          );
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    render(<DiscoverView />);

    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    expect(screen.getByText("Latest")).toBeInTheDocument();
    expect(screen.getByText("Featured")).toBeInTheDocument();
    expect(screen.getByText("Trending")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows a retry-capable error state when the home feed fails to load", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/api/categories")) return Promise.resolve(jsonResponse([]));
        return Promise.resolve(
          new Response(JSON.stringify({ message: "Server unavailable." }), { status: 500 }),
        );
      }),
    );

    render(<DiscoverView />);

    const alerts = await screen.findAllByText("Server unavailable.");
    expect(alerts.length).toBeGreaterThan(0);

    vi.unstubAllGlobals();
  });

  it("switches to a paginated category view when a chip is selected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/api/categories")) {
          return Promise.resolve(
            jsonResponse([
              {
                id: "c1",
                name: "Bridal",
                slug: "bridal",
                category_type: "occasion",
                description: null,
                parent_category_id: null,
                sort_order: 0,
                is_active: true,
              },
            ]),
          );
        }
        if (url.includes("/api/designs/home-feed")) {
          return Promise.resolve(jsonResponse({ latest: [], featured: [], trending: [] }));
        }
        if (url.includes("/api/designs?")) {
          return Promise.resolve(
            jsonResponse({
              items: [sampleDesign],
              page_info: { next_cursor: null, has_more: false },
            }),
          );
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    render(<DiscoverView />);

    const bridalChip = await screen.findByRole("button", { name: "Bridal" });
    fireEvent.click(bridalChip);

    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    expect(screen.queryByText("Latest")).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
