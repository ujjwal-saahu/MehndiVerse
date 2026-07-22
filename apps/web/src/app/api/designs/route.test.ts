import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

function requestWithCookie(url: string, cookie?: string): NextRequest {
  return new NextRequest(url, { headers: cookie ? { cookie } : {} });
}

describe("GET /api/designs", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(requestWithCookie("http://localhost/api/designs"));
    expect(response.status).toBe(401);
  });

  it("forwards query params to the backend and passes through cache-control", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
        {
          status: 200,
          headers: { "cache-control": "public, max-age=30" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      requestWithCookie(
        "http://localhost/api/designs?category_id=abc&sort=trending",
        "mv_access_token=at-123",
      ),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("public, max-age=30");
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/published?category_id=abc&sort=trending");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});
