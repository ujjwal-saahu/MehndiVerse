import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

describe("POST /api/designs/[id]/view", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/view", { method: "POST" }),
      { params: Promise.resolve({ id: "d1" }) },
    );
    expect(response.status).toBe(401);
  });

  it("forwards the view event to the backend and returns 204", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new NextRequest("http://localhost/api/designs/d1/view", {
        method: "POST",
        headers: { cookie: "mv_access_token=at-123" },
      }),
      { params: Promise.resolve({ id: "d1" }) },
    );

    expect(response.status).toBe(204);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/designs/d1/view");
    expect(init.method).toBe("POST");
  });
});
