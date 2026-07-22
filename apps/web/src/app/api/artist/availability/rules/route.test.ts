import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/artist/availability/rules", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/artist/availability/rules"));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's rule list", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/artist/availability/rules", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("POST /api/artist/availability/rules", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/artist/availability/rules", {
      method: "POST",
      body: JSON.stringify({ day_of_week: 1, start_time: "09:00:00", end_time: "17:00:00" }),
    });
    const response = await POST(request);
    expect(response.status).toBe(401);
  });

  it("propagates a 409 when the backend rejects an overlapping rule", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "This overlaps an existing availability rule for the same day.",
          }),
          { status: 409 },
        ),
      ),
    );

    const request = new NextRequest("http://localhost/api/artist/availability/rules", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ day_of_week: 1, start_time: "09:00:00", end_time: "17:00:00" }),
    });
    const response = await POST(request);

    expect(response.status).toBe(409);
  });
});
