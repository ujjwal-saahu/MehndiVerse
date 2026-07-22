// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VerificationQueueView } from "./verification-queue-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleItem = {
  id: "a1",
  user_id: "u1",
  professional_name: "Priya Sharma",
  business_name: null,
  verification_status: "submitted",
  submitted_at: "2026-01-01T00:00:00Z",
  document_count: 2,
};

describe("VerificationQueueView", () => {
  it("shows queued applications once loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({ items: [sampleItem], page_info: { next_cursor: null, has_more: false } }),
        ),
      ),
    );

    render(<VerificationQueueView />);

    expect(await screen.findByText("Priya Sharma")).toBeInTheDocument();
    expect(screen.getByText(/Submitted — awaiting review · 2 documents/)).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows an empty state when nothing matches the filter", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({ items: [], page_info: { next_cursor: null, has_more: false } }),
        ),
      ),
    );

    render(<VerificationQueueView />);

    expect(await screen.findByText("Nothing here")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("refetches with a different status filter when a filter chip is clicked", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url.includes("status_filter=approved")) {
        return Promise.resolve(
          jsonResponse({
            items: [{ ...sampleItem, id: "a2", verification_status: "approved" }],
            page_info: { next_cursor: null, has_more: false },
          }),
        );
      }
      return Promise.resolve(
        jsonResponse({ items: [sampleItem], page_info: { next_cursor: null, has_more: false } }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<VerificationQueueView />);
    await screen.findByText("Priya Sharma");

    fireEvent.click(screen.getByRole("button", { name: "Approved" }));

    await screen.findByText(/Approved · 2 documents/);
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("status_filter=approved")),
    ).toBe(true);

    vi.unstubAllGlobals();
  });
});
