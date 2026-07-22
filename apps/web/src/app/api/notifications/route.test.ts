import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/notifications", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/notifications"));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and query string", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], page_info: {}, unread_count: 0 }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/notifications?unread_only=true", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/notifications?unread_only=true");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});
