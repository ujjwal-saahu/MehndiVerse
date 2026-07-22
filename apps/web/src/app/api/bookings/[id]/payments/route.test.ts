import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/bookings/[id]/payments", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/bookings/b1/payments"), {
      params: Promise.resolve({ id: "b1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/bookings/b1/payments", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request, { params: Promise.resolve({ id: "b1" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/bookings/b1/payments");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("POST /api/bookings/[id]/payments", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/bookings/b1/payments", {
      method: "POST",
      body: JSON.stringify({ payment_type: "deposit" }),
    });
    const response = await POST(request, { params: Promise.resolve({ id: "b1" }) });
    expect(response.status).toBe(401);
  });

  it("propagates a 422 when the payment type doesn't match the booking's status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { message: "A deposit can only be paid while the booking is awaiting one." },
          }),
          { status: 422 },
        ),
      ),
    );

    const request = new NextRequest("http://localhost/api/bookings/b1/payments", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ payment_type: "deposit" }),
    });
    const response = await POST(request, { params: Promise.resolve({ id: "b1" }) });

    expect(response.status).toBe(422);
  });
});
