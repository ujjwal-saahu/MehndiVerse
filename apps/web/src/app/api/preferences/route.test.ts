import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, PATCH } from "./route";

function getRequest(cookie: string | null): NextRequest {
  return new NextRequest("http://localhost/api/preferences", {
    headers: cookie ? { cookie } : {},
  });
}

function patchRequest(
  body: unknown,
  cookie: string | null = "mv_access_token=at-123",
): NextRequest {
  return new NextRequest("http://localhost/api/preferences", {
    method: "PATCH",
    headers: { ...(cookie ? { cookie } : {}), "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("GET /api/preferences", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(getRequest(null));
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ profile_visibility: "public" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(getRequest("mv_access_token=at-123"));

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
  });
});

describe("PATCH /api/preferences", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await PATCH(patchRequest({ show_location: false }, null));
    expect(response.status).toBe(401);
  });

  it("forwards the request body to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ show_location: false }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await PATCH(patchRequest({ show_location: false }));

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ show_location: false });
  });
});
