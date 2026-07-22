// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { CollectionDetailView } from "./collection-detail-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleCollection = {
  id: "c1",
  name: "Bridal Ideas",
  description: null,
  is_default: false,
  is_private: true,
  is_owner: true,
  cover_image_url: null,
  item_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

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
  save_count: 0,
  created_at: "2026-01-01T00:00:00Z",
};

function stubFetch(
  handlers: Partial<{
    collection: () => Response;
    items: () => Response;
    remove: () => Response;
    patch: () => Response;
    del: () => Response;
  }>,
) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/items/reorder")) {
        return Promise.resolve(
          (
            handlers.patch ??
            (() =>
              jsonResponse({
                items: [sampleDesign],
                page_info: { next_cursor: null, has_more: false },
              }))
          )(),
        );
      }
      if (url.includes("/items/") && init?.method === "DELETE") {
        return Promise.resolve((handlers.remove ?? (() => new Response(null, { status: 204 })))());
      }
      if (url.includes("/items")) {
        return Promise.resolve(
          (
            handlers.items ??
            (() =>
              jsonResponse({
                items: [sampleDesign],
                page_info: { next_cursor: null, has_more: false },
              }))
          )(),
        );
      }
      if (init?.method === "DELETE") {
        return Promise.resolve((handlers.del ?? (() => new Response(null, { status: 204 })))());
      }
      if (init?.method === "PATCH") {
        return Promise.resolve((handlers.patch ?? (() => jsonResponse(sampleCollection)))());
      }
      return Promise.resolve((handlers.collection ?? (() => jsonResponse(sampleCollection)))());
    }),
  );
}

describe("CollectionDetailView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the collection name and its items", async () => {
    stubFetch({});
    render(<CollectionDetailView collectionId="c1" />);

    expect(await screen.findByText("Bridal Ideas")).toBeInTheDocument();
    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    expect(screen.getByText("1 design · Private")).toBeInTheDocument();
  });

  it("shows an empty state with no items", async () => {
    stubFetch({
      items: () => jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
    });
    render(<CollectionDetailView collectionId="c1" />);

    expect(await screen.findByText("No designs yet")).toBeInTheDocument();
  });

  it("toggles privacy", async () => {
    stubFetch({
      patch: () => jsonResponse({ ...sampleCollection, is_private: false }),
    });
    render(<CollectionDetailView collectionId="c1" />);
    await screen.findByText("Bridal Ideas");

    fireEvent.click(screen.getByRole("button", { name: "Make public" }));

    await waitFor(() => {
      expect(screen.getByText("1 design · Public")).toBeInTheDocument();
    });
  });

  it("removes an item from the collection", async () => {
    stubFetch({});
    render(<CollectionDetailView collectionId="c1" />);
    await screen.findByText("Bridal Special");

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() => {
      expect(screen.queryByText("Bridal Special")).not.toBeInTheDocument();
    });
  });

  it("deletes the collection and navigates back to the list", async () => {
    vi.stubGlobal(
      "confirm",
      vi.fn(() => true),
    );
    stubFetch({});
    render(<CollectionDetailView collectionId="c1" />);
    await screen.findByText("Bridal Ideas");

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/collections");
    });
  });
});
