import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, POST } from "./route";

describe("POST /api/designs/[id]/save", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/save", { method: "POST" }),
      { params: Promise.resolve({ id: "d1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the save request", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ saved: true, save_count: 2 }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/save", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ saved: true, save_count: 2 });
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/d1/save");
    expect(init.method).toBe("POST");
  });
});

describe("DELETE /api/designs/[id]/save", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards the unsave request", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ saved: false, save_count: 1 }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await DELETE(
      new NextRequest("http://localhost/api/designs/d1/save", {
        method: "DELETE",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ saved: false, save_count: 1 });
  });
});
