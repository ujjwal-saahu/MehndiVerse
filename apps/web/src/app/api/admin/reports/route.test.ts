import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/admin/reports", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/admin/reports"));
    expect(response.status).toBe(401);
  });

  it("forwards the query string to the backend", async () => {
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
      new NextRequest("http://localhost/api/admin/reports?status_filter=pending", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("status_filter=pending");
  });

  it("surfaces a 403 when the caller isn't staff", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "forbidden", message: "Not allowed." } }), {
          status: 403,
        }),
      ),
    );

    const response = await GET(
      new NextRequest("http://localhost/api/admin/reports", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
    );

    expect(response.status).toBe(403);
  });
});
