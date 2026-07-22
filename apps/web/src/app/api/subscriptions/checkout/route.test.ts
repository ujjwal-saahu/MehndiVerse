import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/subscriptions/checkout", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/subscriptions/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_id: "p1" }),
    });
    const response = await POST(request);
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and request body", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ payment_id: "pay1" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/subscriptions/checkout", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ plan_id: "p1" }),
    });
    const response = await POST(request);

    expect(response.status).toBe(201);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/subscriptions/checkout");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});
