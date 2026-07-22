import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/artist/bookings", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/artist/bookings"));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and query string", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest(
      "http://localhost/api/artist/bookings?status_filter=requested",
      { headers: { cookie: "mv_access_token=at-123" } },
    );
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/artist/bookings?status_filter=requested");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});
