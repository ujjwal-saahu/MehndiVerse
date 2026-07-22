import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE } from "./route";

describe("DELETE /api/collections/[id]/items/[designId]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await DELETE(new NextRequest("http://localhost/api/collections/c1/items/d1"), {
      params: Promise.resolve({ id: "c1", designId: "d1" }),
    });
    expect(response.status).toBe(401);
  });

  it("proxies the backend's 204 response", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await DELETE(
      new NextRequest("http://localhost/api/collections/c1/items/d1", {
        method: "DELETE",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "c1", designId: "d1" }) },
    );

    expect(response.status).toBe(204);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/collections/c1/items/d1");
    expect(init.method).toBe("DELETE");
  });
});
