import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/designs/saved", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/designs/saved"));
    expect(response.status).toBe(401);
  });

  it("forwards query params to the backend", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
        {
          status: 200,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new NextRequest("http://localhost/api/designs/saved?limit=5", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/designs/saved?limit=5");
  });
});
