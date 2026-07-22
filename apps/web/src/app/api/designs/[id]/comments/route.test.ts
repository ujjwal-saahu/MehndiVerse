import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/designs/[id]/comments", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/designs/d1/comments"), {
      params: Promise.resolve({ id: "d1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards to the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] }), { status: 200 })),
    );

    const response = await GET(
      new NextRequest("http://localhost/api/designs/d1/comments", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
  });
});

describe("POST /api/designs/[id]/comments", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/comments", { method: "POST" }),
      { params: Promise.resolve({ id: "d1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the create body", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "c1" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/comments", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ body: "Nice!" }),
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ body: "Nice!" });
  });
});
