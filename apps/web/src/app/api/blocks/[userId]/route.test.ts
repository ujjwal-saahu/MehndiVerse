import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE } from "./route";

function deleteRequest(cookie: string | null): NextRequest {
  return new NextRequest("http://localhost/api/blocks/u2", {
    method: "DELETE",
    headers: cookie ? { cookie } : {},
  });
}

describe("DELETE /api/blocks/[userId]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await DELETE(deleteRequest(null), {
      params: Promise.resolve({ userId: "u2" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the unblock request to the backend", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await DELETE(deleteRequest("mv_access_token=at-123"), {
      params: Promise.resolve({ userId: "u2" }),
    });

    expect(response.status).toBe(204);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/users/me/blocks/u2");
    expect(init.method).toBe("DELETE");
  });
});
