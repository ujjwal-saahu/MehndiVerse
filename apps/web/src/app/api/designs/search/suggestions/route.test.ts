import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

function requestWithCookie(url: string, cookie?: string): NextRequest {
  return new NextRequest(url, { headers: cookie ? { cookie } : {} });
}

describe("GET /api/designs/search/suggestions", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(
      requestWithCookie("http://localhost/api/designs/search/suggestions?q=he"),
    );
    expect(response.status).toBe(401);
  });

  it("forwards the query param to the backend", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      requestWithCookie(
        "http://localhost/api/designs/search/suggestions?q=henna",
        "mv_access_token=at-123",
      ),
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/designs/search/suggestions?q=henna");
  });
});
