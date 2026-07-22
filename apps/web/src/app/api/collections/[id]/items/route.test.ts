import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

describe("GET /api/collections/[id]/items", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/collections/c1/items"), {
      params: Promise.resolve({ id: "c1" }),
    });
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
      new NextRequest("http://localhost/api/collections/c1/items?limit=5", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string];
    expect(url).toContain("/collections/c1/items?limit=5");
  });
});

describe("POST /api/collections/[id]/items", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards the add-item body", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
        {
          status: 201,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/collections/c1/items", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ design_id: "d1" }),
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ design_id: "d1" });
  });
});
