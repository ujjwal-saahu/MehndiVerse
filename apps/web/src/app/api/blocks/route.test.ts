import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./route";

function getRequest(cookie: string | null): NextRequest {
  return new NextRequest("http://localhost/api/blocks", {
    headers: cookie ? { cookie } : {},
  });
}

function postRequest(body: unknown, cookie: string | null = "mv_access_token=at-123"): NextRequest {
  return new NextRequest("http://localhost/api/blocks", {
    method: "POST",
    headers: { ...(cookie ? { cookie } : {}), "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("GET /api/blocks", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await GET(getRequest(null));
    expect(response.status).toBe(401);
  });

  it("returns the backend's block list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })),
    );

    const response = await GET(getRequest("mv_access_token=at-123"));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([]);
  });
});

describe("POST /api/blocks", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 when there is no session cookie", async () => {
    const response = await POST(postRequest({ user_id: "u2" }, null));
    expect(response.status).toBe(401);
  });

  it("rejects a request without a user_id", async () => {
    const response = await POST(postRequest({}));
    expect(response.status).toBe(422);
  });

  it("forwards a valid block request to the backend", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ user_id: "u2" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(postRequest({ user_id: "u2" }));

    expect(response.status).toBe(201);
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ user_id: "u2" });
  });
});
