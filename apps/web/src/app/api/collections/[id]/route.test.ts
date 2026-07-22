import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, GET, PATCH } from "./route";

describe("GET /api/collections/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/collections/c1"), {
      params: Promise.resolve({ id: "c1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards to the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "c1" }), { status: 200 })),
    );

    const response = await GET(
      new NextRequest("http://localhost/api/collections/c1", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(200);
  });
});

describe("PATCH /api/collections/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards the update body", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "c1", name: "New" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await PATCH(
      new NextRequest("http://localhost/api/collections/c1", {
        method: "PATCH",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ name: "New" }),
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({ name: "New" });
  });
});

describe("DELETE /api/collections/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("proxies the backend's 204 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    const response = await DELETE(
      new NextRequest("http://localhost/api/collections/c1", {
        method: "DELETE",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(204);
  });
});
