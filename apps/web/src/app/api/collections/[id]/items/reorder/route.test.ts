import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PUT } from "./route";

describe("PUT /api/collections/[id]/items/reorder", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await PUT(
      new NextRequest("http://localhost/api/collections/c1/items/reorder", {
        method: "PUT",
        body: JSON.stringify({ design_ids: ["d1"] }),
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the reorder body", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], page_info: { next_cursor: null, has_more: false } }),
        {
          status: 200,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await PUT(
      new NextRequest("http://localhost/api/collections/c1/items/reorder", {
        method: "PUT",
        headers: { cookie: "mv_access_token=at-123" },
        body: JSON.stringify({ design_ids: ["d2", "d1"] }),
      }),
      { params: Promise.resolve({ id: "c1" }) },
    );

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ design_ids: ["d2", "d1"] });
  });
});
