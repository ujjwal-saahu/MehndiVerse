// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RulesSection } from "./rules-section";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sampleRule = {
  id: "r1",
  day_of_week: 1,
  start_time: "09:00:00",
  end_time: "17:00:00",
  is_active: true,
};

describe("RulesSection", () => {
  it("shows an empty state when there are no rules", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([]))),
    );

    render(<RulesSection />);

    expect(await screen.findByText("No weekly hours set")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("lists existing rules", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([sampleRule]))),
    );

    render(<RulesSection />);

    expect(await screen.findByText("Monday 09:00–17:00")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("creates a new rule via the form", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(
          jsonResponse(
            {
              id: "r2",
              day_of_week: 2,
              start_time: "10:00:00",
              end_time: "12:00:00",
              is_active: true,
            },
            201,
          ),
        );
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<RulesSection />);
    await screen.findByText("No weekly hours set");

    fireEvent.click(screen.getByRole("button", { name: "Add hours" }));

    expect(await screen.findByText("Tuesday 10:00–12:00")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("removes a rule", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "DELETE") {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      return Promise.resolve(jsonResponse([sampleRule]));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<RulesSection />);
    await screen.findByText("Monday 09:00–17:00");

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(await screen.findByText("No weekly hours set")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
