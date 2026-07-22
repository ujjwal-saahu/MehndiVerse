import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/designs/[id]/related", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/designs/d1/related"), {
      params: Promise.resolve({ id: "d1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token to the backend related endpoint", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new NextRequest("http://localhost/api/designs/d1/related", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(200);
    const [url] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/d1/related");
  });
});
