import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/artists/[id]/availability/slots", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(
      new NextRequest(
        "http://localhost/api/artists/a1/availability/slots?service_id=s1&start_date=2026-03-09&end_date=2026-03-09",
      ),
      { params: Promise.resolve({ id: "a1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards query params and the bearer token to the backend", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          artist_profile_id: "a1",
          service_id: "s1",
          artist_timezone: "UTC",
          slots: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest(
      "http://localhost/api/artists/a1/availability/slots?service_id=s1&start_date=2026-03-09&end_date=2026-03-09",
      { headers: { cookie: "mv_access_token=at-123" } },
    );
    const response = await GET(request, { params: Promise.resolve({ id: "a1" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/artists/a1/availability/slots?service_id=s1");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });

  it("propagates a 404 when the backend can't find the artist or service", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "Artist not found." }), { status: 404 }),
        ),
    );

    const request = new NextRequest(
      "http://localhost/api/artists/a1/availability/slots?service_id=s1&start_date=2026-03-09&end_date=2026-03-09",
      { headers: { cookie: "mv_access_token=at-123" } },
    );
    const response = await GET(request, { params: Promise.resolve({ id: "a1" }) });

    expect(response.status).toBe(404);
  });
});
