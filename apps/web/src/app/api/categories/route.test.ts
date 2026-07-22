import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/categories", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/categories"));
    expect(response.status).toBe(401);
  });

  it("forwards query params and returns the backend's categories", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ id: "c1", name: "Bridal" }]), {
        status: 200,
        headers: { "cache-control": "public, max-age=300" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new NextRequest("http://localhost/api/categories?category_type=style", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("public, max-age=300");
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/categories?category_type=style");
  });
});
