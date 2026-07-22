import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/designs/home-feed", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/designs/home-feed"));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's sections", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ latest: [], featured: [], trending: [] }), {
        status: 200,
        headers: { "cache-control": "public, max-age=60" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new NextRequest("http://localhost/api/designs/home-feed", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("public, max-age=60");
    const body = (await response.json()) as { latest: unknown[] };
    expect(body.latest).toEqual([]);
  });
});
