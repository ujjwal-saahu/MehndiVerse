import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, PATCH } from "./route";

describe("GET /api/bookings/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/bookings/b1"), {
      params: Promise.resolve({ id: "b1" }),
    });
    expect(response.status).toBe(401);
  });

  it("propagates a 404 when the booking does not exist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { message: "Booking not found." } }), {
          status: 404,
        }),
      ),
    );

    const request = new NextRequest("http://localhost/api/bookings/b1", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request, { params: Promise.resolve({ id: "b1" }) });

    expect(response.status).toBe(404);
  });
});

describe("PATCH /api/bookings/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/bookings/b1", {
      method: "PATCH",
      body: JSON.stringify({ notes: "hi" }),
    });
    const response = await PATCH(request, { params: Promise.resolve({ id: "b1" }) });
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and the patch body", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "b1", notes: "hi" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/bookings/b1", {
      method: "PATCH",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ notes: "hi" }),
    });
    const response = await PATCH(request, { params: Promise.resolve({ id: "b1" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/bookings/b1");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});
