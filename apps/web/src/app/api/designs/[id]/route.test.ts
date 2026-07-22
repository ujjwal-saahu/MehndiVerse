import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/designs/[id]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/designs/d1"), {
      params: Promise.resolve({ id: "d1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token to the backend detail endpoint", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "d1", title: "Bridal" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new NextRequest("http://localhost/api/designs/d1", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/d1");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });

  it("propagates a 404 from the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: "app_error", message: "Design not found." } }),
          {
            status: 404,
          },
        ),
      ),
    );

    const response = await GET(
      new NextRequest("http://localhost/api/designs/missing", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "missing" }) },
    );

    expect(response.status).toBe(404);
  });
});
