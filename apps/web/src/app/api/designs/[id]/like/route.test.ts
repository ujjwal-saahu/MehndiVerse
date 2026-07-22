import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, POST } from "./route";

describe("POST /api/designs/[id]/like", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/like", { method: "POST" }),
      { params: Promise.resolve({ id: "d1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the like and returns the backend's status", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ liked: true, like_count: 4 }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/like", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ liked: true, like_count: 4 });
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/d1/like");
    expect(init.method).toBe("POST");
  });
});

describe("DELETE /api/designs/[id]/like", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards the unlike request", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ liked: false, like_count: 3 }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await DELETE(
      new NextRequest("http://localhost/api/designs/d1/like", {
        method: "DELETE",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ liked: false, like_count: 3 });
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("DELETE");
  });
});
