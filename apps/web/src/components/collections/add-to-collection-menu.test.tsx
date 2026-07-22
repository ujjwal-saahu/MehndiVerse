// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AddToCollectionMenu } from "./add-to-collection-menu";

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
  item_count: 0,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("AddToCollectionMenu", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists the user's collections when opened", async () => {
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

    render(<AddToCollectionMenu designId="d1" />);
    fireEvent.click(screen.getByRole("button", { name: "Add to collection" }));

    expect(await screen.findByText("Bridal Ideas")).toBeInTheDocument();
  });

  it("adds the design to a collection and marks it added", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }, 201),
        );
      }
      return Promise.resolve(
        jsonResponse({
          items: [sampleCollection],
          page_info: { next_cursor: null, has_more: false },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AddToCollectionMenu designId="d1" />);
    fireEvent.click(screen.getByRole("button", { name: "Add to collection" }));
    const collectionButton = await screen.findByRole("button", { name: /Bridal Ideas/ });
    fireEvent.click(collectionButton);

    expect(await screen.findByText("✓")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === "POST"),
    ).toBe(true);
  });

  it("shows a message when the user has no collections", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
        ),
      ),
    );

    render(<AddToCollectionMenu designId="d1" />);
    fireEvent.click(screen.getByRole("button", { name: "Add to collection" }));

    expect(await screen.findByText("You don't have any collections yet.")).toBeInTheDocument();
  });
});
