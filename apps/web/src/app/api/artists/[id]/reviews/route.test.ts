import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/artists/[id]/reviews", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(new NextRequest("http://localhost/api/artists/a1/reviews"), {
      params: Promise.resolve({ id: "a1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards to the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ items: [], rating_average: 0, rating_count: 0 }), {
          status: 200,
        }),
      ),
    );

    const response = await GET(
      new NextRequest("http://localhost/api/artists/a1/reviews", {
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "a1" }) },
    );

    expect(response.status).toBe(200);
    const body = (await response.json()) as { rating_average: number };
    expect(body.rating_average).toBe(0);
  });
});
