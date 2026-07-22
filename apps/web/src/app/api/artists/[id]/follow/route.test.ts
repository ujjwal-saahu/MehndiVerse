import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DELETE, POST } from "./route";

function requestWithCookie(method: string, cookie?: string): NextRequest {
  return new NextRequest("http://localhost/api/artists/a1/follow", {
    method,
    headers: cookie ? { cookie } : {},
  });
}

describe("POST /api/artists/[id]/follow", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(requestWithCookie("POST"), {
      params: Promise.resolve({ id: "a1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token to the backend and returns 204", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(requestWithCookie("POST", "mv_access_token=at-123"), {
      params: Promise.resolve({ id: "a1" }),
    });

    expect(response.status).toBe(204);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/artists/a1/follow");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });

  it("propagates a 422 when the backend rejects self-follow", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "You cannot follow yourself." }), { status: 422 }),
        ),
    );

    const response = await POST(requestWithCookie("POST", "mv_access_token=at-123"), {
      params: Promise.resolve({ id: "a1" }),
    });

    expect(response.status).toBe(422);
  });
});

describe("DELETE /api/artists/[id]/follow", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await DELETE(requestWithCookie("DELETE"), {
      params: Promise.resolve({ id: "a1" }),
    });
    expect(response.status).toBe(401);
  });

  it("forwards to the backend and returns 204", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    const response = await DELETE(requestWithCookie("DELETE", "mv_access_token=at-123"), {
      params: Promise.resolve({ id: "a1" }),
    });

    expect(response.status).toBe(204);
  });
});
