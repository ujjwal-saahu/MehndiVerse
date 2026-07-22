import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/bookings/[id]/conversation/messages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/bookings/b1/conversation/messages"),
      { params: Promise.resolve({ id: "b1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("propagates a 403 when the caller is not a party to the booking", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ error: { message: "You do not have access to this booking." } }),
            { status: 403 },
          ),
        ),
    );

    const request = new NextRequest("http://localhost/api/bookings/b1/conversation/messages", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request, { params: Promise.resolve({ id: "b1" }) });

    expect(response.status).toBe(403);
  });
});

describe("POST /api/bookings/[id]/conversation/messages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const formData = new FormData();
    formData.set("body", "hi");
    const request = new NextRequest("http://localhost/api/bookings/b1/conversation/messages", {
      method: "POST",
      body: formData,
    });
    const response = await POST(request, { params: Promise.resolve({ id: "b1" }) });
    expect(response.status).toBe(401);
  });

  it("forwards a text-only message as multipart/form-data", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "m1", body: "hi" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchSpy);

    const formData = new FormData();
    formData.set("body", "hi");
    const request = new NextRequest("http://localhost/api/bookings/b1/conversation/messages", {
      method: "POST",
      headers: { cookie: "mv_access_token=at-123" },
      body: formData,
    });
    const response = await POST(request, { params: Promise.resolve({ id: "b1" }) });

    expect(response.status).toBe(201);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/bookings/b1/conversation/messages");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});
