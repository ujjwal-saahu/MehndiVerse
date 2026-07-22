// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BlocksSection } from "./blocks-section";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const wholeDayBlock = {
  id: "b1",
  start_date: "2026-03-10",
  end_date: "2026-03-12",
  block_type: "vacation",
  start_time: null,
  end_time: null,
  reason: "Family trip",
};

describe("BlocksSection", () => {
  it("shows an empty state when there are no blocks", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([]))),
    );

    render(<BlocksSection />);

    expect(await screen.findByText("No blocked dates")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("lists an existing whole-day block", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([wholeDayBlock]))),
    );

    render(<BlocksSection />);

    expect(await screen.findByText(/Vacation/)).toBeInTheDocument();
    expect(screen.getByText(/2026-03-10 – 2026-03-12/)).toBeInTheDocument();
    expect(screen.getByText(/Family trip/)).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("reveals time fields when the manual-block checkbox is checked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([]))),
    );

    render(<BlocksSection />);
    await screen.findByText("No blocked dates");

    expect(screen.queryByText("From")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("checkbox", { name: /Only block specific hours on this day/ }),
    );
    expect(screen.getByText("From")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("removes a block", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "DELETE") {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      return Promise.resolve(jsonResponse([wholeDayBlock]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<BlocksSection />);
    await screen.findByText(/Vacation/);

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(await screen.findByText("No blocked dates")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
