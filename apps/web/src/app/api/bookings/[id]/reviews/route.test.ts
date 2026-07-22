import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/bookings/[id]/reviews", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/bookings/b1/reviews", { method: "POST" }),
      { params: Promise.resolve({ id: "b1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the rating and body", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "rv1", rating: 5 }), { status: 201 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/bookings/b1/reviews", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ rating: 5, body: "Great!" }),
      }),
      { params: Promise.resolve({ id: "b1" }) },
    );

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ rating: 5, body: "Great!" });
  });

  it("surfaces a 409 when the booking already has a review", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ error: { code: "conflict", message: "Already reviewed." } }),
            { status: 409 },
          ),
        ),
    );

    const response = await POST(
      new NextRequest("http://localhost/api/bookings/b1/reviews", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ rating: 3 }),
      }),
      { params: Promise.resolve({ id: "b1" }) },
    );

    expect(response.status).toBe(409);
  });
});
