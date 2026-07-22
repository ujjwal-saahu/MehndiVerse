// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CollectionsView } from "./collections-view";

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
  item_count: 3,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("CollectionsView", () => {
  it("shows the user's collections once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            items: [sampleCollection],
            page_info: { next_cursor: null, has_more: false },
          }),
        ),
      ),
    );

    render(<CollectionsView />);

    expect(await screen.findByText("Bridal Ideas")).toBeInTheDocument();
    expect(screen.getByText("3 designs · Private")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows an empty state when there are no collections", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
        ),
      ),
    );

    render(<CollectionsView />);

    expect(await screen.findByText("No collections yet")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("creates a new collection and prepends it to the list", async () => {
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({ ...sampleCollection, id: "c2", name: "New One" }, 201),
        );
      }
      return Promise.resolve(
        jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<CollectionsView />);
    await screen.findByText("No collections yet");

    fireEvent.click(screen.getByRole("button", { name: "New collection" }));
    fireEvent.change(screen.getByLabelText("Collection name"), { target: { value: "New One" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText("New One")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows a retry-capable error state when loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ message: "Server unavailable." }, 500))),
    );

    render(<CollectionsView />);

    expect(await screen.findByText("Server unavailable.")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
