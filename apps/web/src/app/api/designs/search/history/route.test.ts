import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, GET } from "./route";

function requestWithCookie(url: string, cookie?: string): NextRequest {
  return new NextRequest(url, { headers: cookie ? { cookie } : {} });
}

describe("GET /api/designs/search/history", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(requestWithCookie("http://localhost/api/designs/search/history"));
    expect(response.status).toBe(401);
  });

  it("returns the backend's history list", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify([{ id: "h1", query: "bridal", created_at: "2026-01-01T00:00:00Z" }]),
            { status: 200 },
          ),
        ),
    );

    const response = await GET(
      requestWithCookie("http://localhost/api/designs/search/history", "mv_access_token=at-123"),
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([
      { id: "h1", query: "bridal", created_at: "2026-01-01T00:00:00Z" },
    ]);
  });
});

describe("DELETE /api/designs/search/history", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await DELETE(requestWithCookie("http://localhost/api/designs/search/history"));
    expect(response.status).toBe(401);
  });

  it("proxies the backend's 204 response", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await DELETE(
      requestWithCookie("http://localhost/api/designs/search/history", "mv_access_token=at-123"),
    );

    expect(response.status).toBe(204);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("DELETE");
  });
});
