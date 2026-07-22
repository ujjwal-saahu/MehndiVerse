import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, PATCH } from "./route";

function requestWithCookie(cookie?: string): NextRequest {
  return new NextRequest("http://localhost/api/profile", {
    headers: cookie ? { cookie } : {},
  });
}

function patchRequest(
  body: unknown,
  cookie: string | null = "mv_access_token=at-123",
): NextRequest {
  return new NextRequest("http://localhost/api/profile", {
    method: "PATCH",
    headers: { ...(cookie ? { cookie } : {}), "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("GET /api/profile", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(requestWithCookie());
    expect(response.status).toBe(401);
  });

  it("forwards the bearer token and returns the backend's profile", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ display_name: "Demo User" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(requestWithCookie("mv_access_token=at-123"));

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
    const body = (await response.json()) as { display_name: string };
    expect(body.display_name).toBe("Demo User");
  });
});

describe("PATCH /api/profile", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await PATCH(patchRequest({ bio: "hi" }, null));
    expect(response.status).toBe(401);
  });

  it("forwards the request body to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ bio: "Updated" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await PATCH(patchRequest({ bio: "Updated" }));

    expect(response.status).toBe(200);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({ bio: "Updated" });
  });
});
