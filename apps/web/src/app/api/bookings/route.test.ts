import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/bookings", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/bookings", {
      method: "POST",
      body: JSON.stringify({ artist_profile_id: "a1" }),
    });
    const response = await POST(request);
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and creates a draft", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "b1", status: "draft" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/bookings", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ artist_profile_id: "a1" }),
    });
    const response = await POST(request);

    expect(response.status).toBe(201);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/bookings");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });

  it("propagates a 409 when the artist is not accepting bookings", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { message: "This artist is not currently accepting bookings." },
          }),
          { status: 409 },
        ),
      ),
    );

    const request = new NextRequest("http://localhost/api/bookings", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ artist_profile_id: "a1" }),
    });
    const response = await POST(request);

    expect(response.status).toBe(409);
  });
});
