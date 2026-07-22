import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/artist/services", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/artist/services"));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's service list", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/artist/services", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("POST /api/artist/services", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/artist/services", {
      method: "POST",
      body: JSON.stringify({ name: "Bridal Henna" }),
    });
    const response = await POST(request);
    expect(response.status).toBe(401);
  });

  it("forwards the request body and propagates a validation error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "price_amount is required." }), { status: 422 }),
        ),
    );

    const request = new NextRequest("http://localhost/api/artist/services", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ name: "Bridal Henna", pricing_type: "fixed", currency: "INR" }),
    });
    const response = await POST(request);

    expect(response.status).toBe(422);
  });
});
