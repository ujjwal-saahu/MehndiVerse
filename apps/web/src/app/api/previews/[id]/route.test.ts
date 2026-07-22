import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, GET, PATCH } from "./route";

describe("GET /api/previews/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/previews/p1"), {
      params: Promise.resolve({ id: "p1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "p1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new NextRequest("http://localhost/api/previews/p1", {
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await GET(request, { params: Promise.resolve({ id: "p1" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/previews/p1");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("PATCH /api/previews/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await PATCH(
      new NextRequest("http://localhost/api/previews/p1", {
        method: "PATCH",
        body: new FormData(),
      }),
      { params: Promise.resolve({ id: "p1" }) },
    );
    expect(response.status).toBe(401);
  });
});

describe("DELETE /api/previews/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await DELETE(
      new NextRequest("http://localhost/api/previews/p1", { method: "DELETE" }),
      { params: Promise.resolve({ id: "p1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("returns 204 on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const request = new NextRequest("http://localhost/api/previews/p1", {
      method: "DELETE",
      headers: { cookie: "mv_access_token=at-123" },
    });
    const response = await DELETE(request, { params: Promise.resolve({ id: "p1" }) });
    expect(response.status).toBe(204);
  });
});
