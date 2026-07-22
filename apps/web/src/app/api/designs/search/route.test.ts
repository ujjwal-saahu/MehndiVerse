import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

function requestWithCookie(url: string, cookie?: string): NextRequest {
  return new NextRequest(url, { headers: cookie ? { cookie } : {} });
}

describe("GET /api/designs/search", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(requestWithCookie("http://localhost/api/designs/search"));
    expect(response.status).toBe(401);
  });

  it("forwards query params and the auth header to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      requestWithCookie(
        "http://localhost/api/designs/search?q=bridal&sort=newest&category_id=c1&category_id=c2",
        "mv_access_token=at-123",
      ),
    );

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/search?q=bridal&sort=newest&category_id=c1&category_id=c2");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });

  it("propagates the backend's error message and status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "rate_limited", message: "Slow down." } }), {
          status: 429,
        }),
      ),
    );

    const response = await GET(
      requestWithCookie("http://localhost/api/designs/search", "mv_access_token=at-123"),
    );

    expect(response.status).toBe(429);
    expect(await response.json()).toEqual({ message: "Slow down." });
  });
});
