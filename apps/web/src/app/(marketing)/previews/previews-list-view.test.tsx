// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PreviewsListView } from "./previews-list-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleItem = {
  id: "p1",
  design: { id: "d1", title: "Bridal Special", thumbnail_url: null, is_premium: false },
  source_image_url: "https://example.test/source.jpg",
  result_image_url: null,
  overlay_transform: null,
  source_width: 800,
  source_height: 600,
  status: "completed",
  error_message: null,
  shared_with_booking_id: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

describe("PreviewsListView", () => {
  it("shows an empty state when there are no previews", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([]))),
    );

    render(<PreviewsListView />);

    expect(await screen.findByText("No previews yet")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows saved previews once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([sampleItem]))),
    );

    render(<PreviewsListView />);

    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows a retry-capable error state when loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 500 }))),
    );

    render(<PreviewsListView />);

    expect(await screen.findByText("Could not load your previews.")).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
