// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { SearchView } from "./search-view";

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

function stubFetch(
  handlers: Partial<{
    search: () => Response;
    suggestions: () => Response;
    history: () => Response;
    categories: () => Response;
  }>,
) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/api/designs/search/suggestions")) {
        return Promise.resolve((handlers.suggestions ?? (() => jsonResponse([])))());
      }
      if (url.includes("/api/designs/search/history")) {
        if (init?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
        return Promise.resolve((handlers.history ?? (() => jsonResponse([])))());
      }
      if (url.includes("/api/designs/search")) {
        return Promise.resolve(
          (
            handlers.search ??
            (() =>
              jsonResponse({
                items: [sampleDesign],
                page_info: { next_cursor: null, has_more: false },
              }))
          )(),
        );
      }
      if (url.includes("/api/categories")) {
        return Promise.resolve((handlers.categories ?? (() => jsonResponse([])))());
      }
      return Promise.resolve(jsonResponse({}));
    }),
  );
}

describe("SearchView", () => {
  it("shows results loaded on mount", async () => {
    stubFetch({});
    render(<SearchView />);

    expect(await screen.findByText("Bridal Special")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows an empty state with a clear-filters action when filtered results are empty", async () => {
    stubFetch({
      search: () => jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
      categories: () =>
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
    });
    render(<SearchView />);

    expect(await screen.findByText("No designs found")).toBeInTheDocument();

    const checkbox = await screen.findByRole("checkbox", { name: "Bridal" });
    fireEvent.click(checkbox);

    expect(await screen.findByText("Clear filters")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("submitting a keyword search re-fetches results", async () => {
    stubFetch({});
    render(<SearchView />);
    await screen.findByText("Bridal Special");

    const input = screen.getByLabelText("Search designs");
    fireEvent.change(input, { target: { value: "peacock" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
      expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("q=peacock"))).toBe(true);
    });
    vi.unstubAllGlobals();
  });

  it("selecting a design suggestion navigates to the design detail page", async () => {
    stubFetch({
      suggestions: () => jsonResponse([{ type: "design", id: "d1", label: "Bridal Special" }]),
    });
    render(<SearchView />);
    await screen.findByText("Bridal Special");

    const input = screen.getByLabelText("Search designs");
    fireEvent.change(input, { target: { value: "brid" } });

    const option = await screen.findByRole("option", { name: /Bridal Special/ });
    fireEvent.click(option);

    expect(pushMock).toHaveBeenCalledWith("/designs/d1");
    vi.unstubAllGlobals();
  });

  it("shows and clears recent searches", async () => {
    stubFetch({
      history: () =>
        jsonResponse([{ id: "h1", query: "bridal", created_at: "2026-01-01T00:00:00Z" }]),
    });
    render(<SearchView />);

    const recentChip = await screen.findByRole("button", { name: "bridal" });
    expect(recentChip).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear" }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "bridal" })).not.toBeInTheDocument();
    });
    vi.unstubAllGlobals();
  });

  it("shows a retry-capable error state when the search fails", async () => {
    stubFetch({
      search: () =>
        new Response(JSON.stringify({ message: "Server unavailable." }), { status: 500 }),
    });
    render(<SearchView />);

    expect(await screen.findByText("Server unavailable.")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("shows a load-more button and appends the next page", async () => {
    let call = 0;
    stubFetch({
      search: () => {
        call += 1;
        if (call === 1) {
          return jsonResponse({
            items: [sampleDesign],
            page_info: { next_cursor: "cursor-1", has_more: true },
          });
        }
        return jsonResponse({
          items: [{ ...sampleDesign, id: "d2", title: "Second Design" }],
          page_info: { next_cursor: null, has_more: false },
        });
      },
    });
    render(<SearchView />);

    await screen.findByText("Bridal Special");
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    expect(await screen.findByText("Second Design")).toBeInTheDocument();
    expect(screen.getByText("Bridal Special")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
