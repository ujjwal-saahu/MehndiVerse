import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/previews/[id]/send-to-artist", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const request = new NextRequest("http://localhost/api/previews/p1/send-to-artist", {
      method: "POST",
      body: JSON.stringify({ booking_id: "b1" }),
    });
    const response = await POST(request, { params: Promise.resolve({ id: "p1" }) });
    expect(response.status).toBe(401);
  });

  it("forwards the booking id", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "p1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/previews/p1/send-to-artist", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: JSON.stringify({ booking_id: "b1" }),
    });
    const response = await POST(request, { params: Promise.resolve({ id: "p1" }) });

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/previews/p1/send-to-artist");
  });
});
