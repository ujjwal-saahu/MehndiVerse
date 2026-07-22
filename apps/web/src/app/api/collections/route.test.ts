import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/collections", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/collections"));
    expect(response.status).toBe(401);
  });

  it("forwards to the backend", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
        {
          status: 200,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new NextRequest("http://localhost/api/collections", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/collections");
  });
});

describe("POST /api/collections", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/collections", {
        method: "POST",
        body: JSON.stringify({ name: "Bridal" }),
      }),
    );
    expect(response.status).toBe(401);
  });

  it("creates a collection via the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "c1", name: "Bridal" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/collections", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ name: "Bridal" }),
      }),
    );

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ name: "Bridal" });
  });
});
