import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/admin/artists", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/admin/artists"));
    expect(response.status).toBe(401);
  });

  it("forwards query parameters to the backend queue endpoint", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
        {
          status: 200,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest(
      "http://localhost/api/admin/artists?status_filter=submitted&limit=10",
      { headers: { cookie: "mv_access_token=at-123" } },
    );
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/admin/artists?status_filter=submitted&limit=10");
  });
});
