// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ModerationQueueView } from "./moderation-queue-view";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleReport = {
  id: "r1",
  reporter_id: "u1",
  reported_entity_type: "design",
  reported_entity_id: "d1",
  status: "pending",
  reason: "This looks stolen",
  resolution_notes: null,
  resolved_by: null,
  resolved_at: null,
  created_at: "2026-01-01T00:00:00Z",
  entity_snapshot: { title: "Bridal mandala", status: "published" },
};

describe("ModerationQueueView", () => {
  it("shows pending reports once loaded, including the entity snapshot", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            items: [sampleReport],
            page_info: { next_cursor: null, has_more: false },
          }),
        ),
      ),
    );

    render(<ModerationQueueView canAct={false} />);

    expect(await screen.findByText("This looks stolen")).toBeInTheDocument();
    expect(screen.getByText(/Bridal mandala/)).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("hides resolve/dismiss actions when the viewer cannot act", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            items: [sampleReport],
            page_info: { next_cursor: null, has_more: false },
          }),
        ),
      ),
    );

    render(<ModerationQueueView canAct={false} />);
    await screen.findByText("This looks stolen");

    expect(screen.queryByRole("button", { name: "Resolve" })).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("lets a viewer who can act resolve a report", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(jsonResponse({ ...sampleReport, status: "resolved" }));
      }
      return Promise.resolve(
        jsonResponse({ items: [sampleReport], page_info: { next_cursor: null, has_more: false } }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "prompt").mockReturnValue("Checked, actioned separately");

    render(<ModerationQueueView canAct={true} />);
    await screen.findByText("This looks stolen");

    fireEvent.click(screen.getByRole("button", { name: "Resolve" }));

    await screen.findByText(/design · resolved/);
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("/api/admin/reports/r1/resolve")),
    ).toBe(true);

    vi.unstubAllGlobals();
    vi.restoreAllMocks();
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

    render(<ModerationQueueView canAct={false} />);

    expect(await screen.findByText("Nothing here")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
