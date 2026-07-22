// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DesignDetailView } from "./design-detail-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleDesign = {
  id: "d1",
  artist_profile_id: "a1",
  artist: {
    id: "a1",
    display_name: "Henna by Asha",
    avatar_url: null,
    headline: "Bridal specialist",
    rating_average: 4.8,
    rating_count: 12,
    is_accepting_bookings: true,
  },
  title: "Bridal Special",
  description: "An elaborate bridal design.",
  difficulty_level: "advanced",
  body_placement: "hand",
  status: "published",
  is_featured: false,
  is_premium: false,
  view_count: 3,
  like_count: 0,
  save_count: 0,
  is_liked: false,
  is_saved: false,
  categories: [
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
  ],
  tags: ["wedding"],
  images: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("DesignDetailView", () => {
  it("shows the design, artist, and categories once loaded, and pings the view endpoint", async () => {
    const fetchSpy = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/related")) return Promise.resolve(jsonResponse([]));
      if (url.endsWith("/view") && init?.method === "POST") {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      if (url.includes("/api/designs/d1")) return Promise.resolve(jsonResponse(sampleDesign));
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(<DesignDetailView designId="d1" />);

    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    expect(screen.getByText("An elaborate bridal design.")).toBeInTheDocument();
    expect(screen.getByText("Henna by Asha")).toBeInTheDocument();
    expect(screen.getByText("Bridal")).toBeInTheDocument();

    await vi.waitFor(() => {
      expect(fetchSpy.mock.calls.some(([url]) => String(url).endsWith("/view"))).toBe(true);
    });

    vi.unstubAllGlobals();
  });

  it("shows a retry-capable error state when the design fails to load", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ message: "Design not found." }, 404))),
    );

    render(<DesignDetailView designId="missing" />);

    expect(await screen.findByText("Design not found.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
